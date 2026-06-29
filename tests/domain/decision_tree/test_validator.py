"""Synthetic tests for reusable tree-structure validation."""

from types import MappingProxyType
from typing import Any
from uuid import UUID

import pytest

from cdss.domain.decision_tree import (
    ContextPatchError,
    EdgeDefinition,
    InvalidConditionDefinition,
    InvalidStartNode,
    InvalidTreeStructure,
    NodeDefinition,
    NodeType,
    TreeDefinition,
    TreeGraph,
    validate_tree_graph,
)

TREE_ID = UUID(int=100)
OTHER_TREE_ID = UUID(int=200)
TREE = TreeDefinition(
    id=TREE_ID,
    tree_key="synthetic-tree",
    name_en="Synthetic tree",
    name_vi="Cay tong hop",
)


def _node(
    serial: int,
    node_key: str,
    node_type: NodeType,
    **values: Any,
) -> NodeDefinition:
    return NodeDefinition(
        id=UUID(int=serial),
        tree_id=TREE_ID,
        node_key=node_key,
        node_type=node_type,
        text_en=node_key,
        text_vi=node_key,
        display_order=serial,
        **values,
    )


def _edge(
    serial: int,
    source: NodeDefinition,
    target: NodeDefinition,
    traversal_order: int = 1,
    **values: Any,
) -> EdgeDefinition:
    from_tree_id = values.pop("from_tree_id", TREE_ID)
    to_tree_id = values.pop("to_tree_id", TREE_ID)
    return EdgeDefinition(
        id=UUID(int=serial),
        from_node_id=source.id,
        to_node_id=target.id,
        traversal_order=traversal_order,
        from_tree_id=from_tree_id,
        to_tree_id=to_tree_id,
        **values,
    )


def _graph(
    nodes: list[NodeDefinition],
    edges: list[EdgeDefinition],
    *,
    start_node: NodeDefinition | None = None,
) -> TreeGraph:
    nodes_by_id = {node.id: node for node in nodes}
    outgoing: dict[UUID, list[EdgeDefinition]] = {node.id: [] for node in nodes}
    for edge in edges:
        outgoing.setdefault(edge.from_node_id, []).append(edge)
    selected_start = start_node or next(
        (node for node in nodes if node.node_type is NodeType.START), nodes[0]
    )
    return TreeGraph(
        tree=TREE,
        start_node=selected_start,
        nodes_by_id=MappingProxyType(nodes_by_id),
        nodes_by_key=MappingProxyType({node.node_key: node for node in nodes}),
        outgoing_edges_by_node_id=MappingProxyType(
            {node_id: tuple(node_edges) for node_id, node_edges in outgoing.items()}
        ),
        references_by_node_id=MappingProxyType({node.id: () for node in nodes}),
        global_nodes=tuple(node for node in nodes if node.node_type is NodeType.GLOBAL),
    )


def _valid_graph() -> TreeGraph:
    start = _node(1, "start", NodeType.START)
    condition = _node(
        2,
        "condition",
        NodeType.CONDITION,
        condition_definition={"path": "input.value", "op": "eq", "value": 1},
    )
    inference = _node(
        3,
        "inference",
        NodeType.INFERENCE,
        context_patch={"derived": {"value": True}},
    )
    end = _node(4, "end", NodeType.END)
    return _graph(
        [start, condition, inference, end],
        [
            _edge(11, start, condition),
            _edge(12, condition, inference),
            _edge(13, inference, end),
        ],
    )


def test_valid_graph_has_no_warnings_without_link_catalog() -> None:
    result = validate_tree_graph(_valid_graph())

    assert result.model_dump(mode="json") == {
        "tree_key": "synthetic-tree",
        "warnings": [],
    }


@pytest.mark.parametrize("start_count", [0, 2])
def test_requires_exactly_one_start_node(start_count: int) -> None:
    nodes = [_node(10, "action", NodeType.ACTION)]
    nodes.extend(_node(index + 1, f"start-{index}", NodeType.START) for index in range(start_count))
    graph = _graph(nodes, [], start_node=nodes[0])

    with pytest.raises(InvalidStartNode):
        validate_tree_graph(graph)


def test_rejects_cross_tree_edge() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(2, "action", NodeType.ACTION)
    edge = _edge(10, start, action, to_tree_id=OTHER_TREE_ID)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(_graph([start, action], [edge]))

    assert exc_info.value.details["reason"] == "cross_tree_or_missing_edge_endpoint"


def test_start_requires_outgoing_edge() -> None:
    start = _node(1, "start", NodeType.START)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(_graph([start], []))

    assert exc_info.value.details["reason"] == "node_requires_outgoing_edge"


@pytest.mark.parametrize("node_type", [NodeType.CONDITION, NodeType.INFERENCE])
def test_branching_node_requires_outgoing_edge(node_type: NodeType) -> None:
    start = _node(1, "start", NodeType.START)
    values: dict[str, Any] = {}
    if node_type is NodeType.CONDITION:
        values["condition_definition"] = {
            "path": "input.value",
            "op": "eq",
            "value": 1,
        }
    branching_node = _node(2, "branch", node_type, **values)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(_graph([start, branching_node], [_edge(10, start, branching_node)]))

    assert exc_info.value.node_key == "branch"
    assert exc_info.value.details["reason"] == "node_requires_outgoing_edge"


@pytest.mark.parametrize("node_type", [NodeType.END, NodeType.LINK])
def test_terminal_node_rejects_internal_outgoing_edge(node_type: NodeType) -> None:
    start = _node(1, "start", NodeType.START)
    values = {"link_target_tree_key": "target-tree"} if node_type is NodeType.LINK else {}
    terminal = _node(2, "terminal", node_type, **values)
    action = _node(3, "action", NodeType.ACTION)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(
            _graph(
                [start, terminal, action],
                [_edge(10, start, terminal), _edge(11, terminal, action)],
            )
        )

    assert exc_info.value.details["reason"] == "terminal_node_has_internal_edge"


def test_link_requires_target_tree_key() -> None:
    start = _node(1, "start", NodeType.START)
    link = _node(2, "link", NodeType.LINK)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(_graph([start, link], [_edge(10, start, link)]))

    assert exc_info.value.details["reason"] == "link_target_tree_key_required"


def test_link_may_be_a_conditional_candidate() -> None:
    start = _node(1, "start", NodeType.START)
    link = _node(
        2,
        "link",
        NodeType.LINK,
        condition_definition={
            "path": "input.facility_capability",
            "op": "eq",
            "value": "FULL_RESOURCES",
        },
        link_target_tree_key="target-tree",
    )

    result = validate_tree_graph(_graph([start, link], [_edge(10, start, link)]))

    assert result.warnings == []


def test_every_executable_node_must_be_reachable() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(2, "action", NodeType.ACTION)
    orphan = _node(3, "orphan", NodeType.ACTION)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(_graph([start, action, orphan], [_edge(10, start, action)]))

    assert exc_info.value.details == {
        "reason": "unreachable_executable_nodes",
        "unreachable_node_keys": ["orphan"],
    }


def test_global_node_is_exempt_from_reachability() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(2, "action", NodeType.ACTION)
    global_node = _node(3, "global", NodeType.GLOBAL, global_config={"unit": "mmHg"})

    result = validate_tree_graph(_graph([start, action, global_node], [_edge(10, start, action)]))

    assert result.warnings == []


def test_rejects_internal_cycle() -> None:
    start = _node(1, "start", NodeType.START)
    first = _node(2, "first", NodeType.ACTION)
    second = _node(3, "second", NodeType.ACTION)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(
            _graph(
                [start, first, second],
                [
                    _edge(10, start, first),
                    _edge(11, first, second),
                    _edge(12, second, first),
                ],
            )
        )

    assert exc_info.value.details["reason"] == "internal_graph_cycle"


def test_rejects_duplicate_outgoing_traversal_order() -> None:
    start = _node(1, "start", NodeType.START)
    first = _node(2, "first", NodeType.ACTION)
    second = _node(3, "second", NodeType.ACTION)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(
            _graph(
                [start, first, second],
                [_edge(10, start, first, 1), _edge(11, start, second, 1)],
            )
        )

    assert exc_info.value.details["reason"] == "duplicate_outgoing_traversal_order"


def test_condition_definition_must_match_evaluator_grammar() -> None:
    start = _node(1, "start", NodeType.START)
    condition = _node(
        2,
        "condition",
        NodeType.CONDITION,
        condition_definition={"all": []},
    )
    end = _node(3, "end", NodeType.END)

    with pytest.raises(InvalidConditionDefinition):
        validate_tree_graph(
            _graph(
                [start, condition, end],
                [_edge(10, start, condition), _edge(11, condition, end)],
            )
        )


def test_condition_runtime_paths_require_input_or_context_root() -> None:
    start = _node(1, "start", NodeType.START)
    condition = _node(
        2,
        "condition",
        NodeType.CONDITION,
        condition_definition={"path": "patient.value", "op": "eq", "value": 1},
    )
    end = _node(3, "end", NodeType.END)

    with pytest.raises(InvalidConditionDefinition) as exc_info:
        validate_tree_graph(
            _graph(
                [start, condition, end],
                [_edge(10, start, condition), _edge(11, condition, end)],
            )
        )

    assert exc_info.value.details["reason"] == "invalid_left_path"


@pytest.mark.parametrize(
    ("from_path", "to_path", "expected_reason"),
    [
        ("patient.source", "context.target", "invalid_copy_source_path"),
        ("input.source", "input.target", "invalid_copy_target_path"),
    ],
)
def test_copy_path_roots_are_validated(from_path: str, to_path: str, expected_reason: str) -> None:
    start = _node(1, "start", NodeType.START)
    inference = _node(
        2,
        "inference",
        NodeType.INFERENCE,
        context_patch={
            "operations": [
                {
                    "op": "COPY_PATH",
                    "from_path": from_path,
                    "to_path": to_path,
                    "required": True,
                }
            ]
        },
    )
    end = _node(3, "end", NodeType.END)

    with pytest.raises(ContextPatchError) as exc_info:
        validate_tree_graph(
            _graph(
                [start, inference, end],
                [_edge(10, start, inference), _edge(11, inference, end)],
            )
        )

    assert exc_info.value.details["reason"] == expected_reason


def test_terminal_action_is_valid() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(2, "action", NodeType.ACTION, action_payload={"kind": "monitor"})

    result = validate_tree_graph(_graph([start, action], [_edge(10, start, action)]))

    assert result.warnings == []


def test_end_node_may_have_context_patch_and_action_payload() -> None:
    start = _node(1, "start", NodeType.START)
    end = _node(
        2,
        "end",
        NodeType.END,
        context_patch={"status": "complete"},
        action_payload={"kind": "maintain"},
    )

    result = validate_tree_graph(_graph([start, end], [_edge(10, start, end)]))

    assert result.warnings == []


def test_unseeded_link_target_is_warning_by_default() -> None:
    start = _node(1, "start", NodeType.START)
    link = _node(2, "link", NodeType.LINK, link_target_tree_key="external-tree")
    graph = _graph([start, link], [_edge(10, start, link)])

    result = validate_tree_graph(graph, available_tree_keys={TREE.tree_key})

    assert [warning.model_dump(mode="json") for warning in result.warnings] == [
        {
            "code": "unseeded_link_target",
            "message": "Linked target tree is not currently available.",
            "tree_key": "synthetic-tree",
            "node_key": "link",
            "details": {"target_tree_key": "external-tree"},
        }
    ]


def test_strict_mode_rejects_unseeded_link_target() -> None:
    start = _node(1, "start", NodeType.START)
    link = _node(2, "link", NodeType.LINK, link_target_tree_key="external-tree")
    graph = _graph([start, link], [_edge(10, start, link)])

    with pytest.raises(InvalidTreeStructure) as exc_info:
        validate_tree_graph(
            graph,
            available_tree_keys={TREE.tree_key},
            strict_link_targets=True,
        )

    assert exc_info.value.details["reason"] == "unseeded_link_target"


def test_available_link_target_has_no_warning() -> None:
    start = _node(1, "start", NodeType.START)
    link = _node(2, "link", NodeType.LINK, link_target_tree_key="available-tree")
    graph = _graph([start, link], [_edge(10, start, link)])

    result = validate_tree_graph(
        graph,
        available_tree_keys={TREE.tree_key, "available-tree"},
    )

    assert result.warnings == []
