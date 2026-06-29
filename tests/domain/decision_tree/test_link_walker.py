"""Synthetic tests for cross-tree links and evidence aggregation."""

from collections.abc import Sequence
from dataclasses import replace
from types import MappingProxyType
from typing import Any
from uuid import UUID

import pytest

from cdss.domain.decision_tree import (
    EdgeDefinition,
    LinkTargetNodeNotFound,
    LinkTargetNotFound,
    NodeDefinition,
    NodeType,
    SourceReferenceDefinition,
    TraceEvent,
    TraversalCycleDetected,
    TraversalLimitExceeded,
    TraversalTraceEntry,
    TreeDefinition,
    TreeGraph,
    TreeNotFound,
    walk_tree,
)


class InMemoryGraphRepository:
    def __init__(self, graphs: list[TreeGraph]) -> None:
        self.graphs = {graph.tree.tree_key: graph for graph in graphs}

    def get_tree(self, tree_key: str) -> TreeGraph:
        try:
            return self.graphs[tree_key]
        except KeyError as exc:
            raise TreeNotFound(tree_key=tree_key) from exc


def _tree(serial: int, tree_key: str) -> TreeDefinition:
    return TreeDefinition(
        id=UUID(int=serial),
        tree_key=tree_key,
        name_en=tree_key,
        name_vi=tree_key,
    )


def _node(
    tree: TreeDefinition,
    serial: int,
    node_key: str,
    node_type: NodeType,
    **values: Any,
) -> NodeDefinition:
    return NodeDefinition(
        id=UUID(int=serial),
        tree_id=tree.id,
        node_key=node_key,
        node_type=node_type,
        text_en=node_key,
        text_vi=node_key,
        display_order=serial,
        **values,
    )


def _edge(
    tree: TreeDefinition,
    serial: int,
    source: NodeDefinition,
    target: NodeDefinition,
    traversal_order: int = 1,
) -> EdgeDefinition:
    return EdgeDefinition(
        id=UUID(int=serial),
        from_node_id=source.id,
        to_node_id=target.id,
        traversal_order=traversal_order,
        from_tree_id=tree.id,
        to_tree_id=tree.id,
    )


def _reference(
    serial: int,
    node: NodeDefinition,
    reference_order: int,
    title: str,
) -> SourceReferenceDefinition:
    return SourceReferenceDefinition(
        id=UUID(int=serial),
        node_id=node.id,
        source_title=title,
        section_path=["section", str(reference_order)],
        reference_order=reference_order,
        locator="table",
        locator_detail="row 1",
        printed_page_numbers=(10,),
        pdf_page_numbers=(20,),
        reference_note="note",
    )


def _graph(
    tree: TreeDefinition,
    nodes: list[NodeDefinition],
    edges: list[EdgeDefinition],
    references: list[SourceReferenceDefinition] | None = None,
) -> TreeGraph:
    return TreeGraph.build(
        tree=tree,
        nodes=nodes,
        edges=edges,
        references=references or [],
    )


def _entered(trace: Sequence[TraversalTraceEntry]) -> list[tuple[str, str]]:
    return [
        (entry.tree_key, entry.node_key)
        for entry in trace
        if entry.event is TraceEvent.NODE_ENTERED
    ]


def test_link_without_target_node_continues_from_target_start_and_does_not_return() -> None:
    source_tree = _tree(100, "source-tree")
    source_start = _node(source_tree, 101, "source-start", NodeType.START)
    link = _node(
        source_tree,
        102,
        "to-target",
        NodeType.LINK,
        link_target_tree_key="target-tree",
    )
    source_action = _node(
        source_tree,
        104,
        "source-action",
        NodeType.ACTION,
        action_payload={"result": "source-complete"},
        context_patch={"source_context": True},
    )
    source_global = _node(
        source_tree,
        103,
        "source-global",
        NodeType.GLOBAL,
        global_config={"source_setting": True},
    )
    source_graph = _graph(
        source_tree,
        [source_start, source_action, link, source_global],
        [
            _edge(source_tree, 110, source_start, source_action),
            _edge(source_tree, 111, source_action, link),
        ],
    )

    target_tree = _tree(200, "target-tree")
    target_start = _node(target_tree, 201, "target-start", NodeType.START)
    target_action = _node(
        target_tree,
        202,
        "target-action",
        NodeType.ACTION,
        action_payload={"result": "target-complete"},
    )
    target_global = _node(
        target_tree,
        203,
        "target-global",
        NodeType.GLOBAL,
        global_config={"target_setting": 1},
    )
    target_graph = _graph(
        target_tree,
        [target_start, target_action, target_global],
        [_edge(target_tree, 210, target_start, target_action)],
    )

    result = walk_tree(
        source_graph,
        {"shared_input": {"value": 1}},
        repository=InMemoryGraphRepository([source_graph, target_graph]),
    )

    assert _entered(result.trace) == [
        ("source-tree", "source-start"),
        ("source-tree", "source-action"),
        ("source-tree", "to-target"),
        ("target-tree", "target-start"),
        ("target-tree", "target-action"),
    ]
    assert [action.payload for action in result.actions] == [
        {"result": "source-complete"},
        {"result": "target-complete"},
    ]
    assert result.input_snapshot.to_dict() == {"shared_input": {"value": 1}}
    assert result.context == {"source_context": True}
    assert [metadata.tree_key for metadata in result.tree_metadata] == [
        "source-tree",
        "target-tree",
    ]
    assert result.tree_metadata[0].global_config == [{"source_setting": True}]
    assert result.tree_metadata[1].global_config == [{"target_setting": 1}]
    assert all(entry.node_type is not NodeType.GLOBAL for entry in result.trace)


def test_link_with_target_node_enters_exact_node_without_target_start() -> None:
    source_tree = _tree(100, "source-tree")
    source_start = _node(source_tree, 101, "source-start", NodeType.START)
    link = _node(
        source_tree,
        102,
        "to-exact",
        NodeType.LINK,
        link_target_tree_key="target-tree",
        link_target_node_key="exact-action",
    )
    source_graph = _graph(
        source_tree,
        [source_start, link],
        [_edge(source_tree, 110, source_start, link)],
    )

    target_tree = _tree(200, "target-tree")
    target_start = _node(target_tree, 201, "target-start", NodeType.START)
    default_action = _node(target_tree, 202, "default-action", NodeType.ACTION)
    exact_action = _node(
        target_tree,
        203,
        "exact-action",
        NodeType.ACTION,
        action_payload={"selected": "exact"},
    )
    target_graph = _graph(
        target_tree,
        [target_start, default_action, exact_action],
        [_edge(target_tree, 210, target_start, default_action)],
    )

    result = walk_tree(
        source_graph,
        {},
        repository=InMemoryGraphRepository([target_graph]),
    )

    assert _entered(result.trace)[-1] == ("target-tree", "exact-action")
    assert ("target-tree", "target-start") not in _entered(result.trace)
    assert [action.payload for action in result.actions] == [{"selected": "exact"}]


def test_missing_link_target_tree_raises_typed_error_with_partial_state() -> None:
    source_tree = _tree(100, "source-tree")
    start = _node(source_tree, 101, "start", NodeType.START)
    action = _node(
        source_tree,
        102,
        "prepare",
        NodeType.ACTION,
        action_payload={"step": "prepare"},
        context_patch={"prepared": True},
    )
    link = _node(
        source_tree,
        103,
        "missing-link",
        NodeType.LINK,
        link_target_tree_key="missing-tree",
    )
    link_reference = _reference(120, link, 1, "Link evidence")
    source_graph = _graph(
        source_tree,
        [start, action, link],
        [_edge(source_tree, 110, start, action), _edge(source_tree, 111, action, link)],
        [link_reference],
    )

    with pytest.raises(LinkTargetNotFound) as exc_info:
        walk_tree(source_graph, {}, repository=InMemoryGraphRepository([]))

    partial = exc_info.value.partial_run_state
    assert partial is not None
    assert partial.context == {"prepared": True}
    assert [item.payload for item in partial.actions] == [{"step": "prepare"}]
    assert _entered(partial.trace)[-1] == ("source-tree", "missing-link")
    assert [(reference.node_key, reference.source_title) for reference in partial.references] == [
        ("missing-link", "Link evidence")
    ]


def test_missing_requested_target_node_raises_typed_error() -> None:
    source_tree = _tree(100, "source-tree")
    start = _node(source_tree, 101, "start", NodeType.START)
    link = _node(
        source_tree,
        102,
        "link",
        NodeType.LINK,
        link_target_tree_key="target-tree",
        link_target_node_key="missing-node",
    )
    source_graph = _graph(
        source_tree,
        [start, link],
        [_edge(source_tree, 110, start, link)],
    )
    target_tree = _tree(200, "target-tree")
    target_start = _node(target_tree, 201, "target-start", NodeType.START)
    target_action = _node(target_tree, 202, "target-action", NodeType.ACTION)
    target_graph = _graph(
        target_tree,
        [target_start, target_action],
        [_edge(target_tree, 210, target_start, target_action)],
    )

    with pytest.raises(LinkTargetNodeNotFound) as exc_info:
        walk_tree(
            source_graph,
            {},
            repository=InMemoryGraphRepository([target_graph]),
        )

    assert exc_info.value.tree_key == "target-tree"
    assert exc_info.value.node_key == "missing-node"
    assert exc_info.value.partial_run_state is not None


def test_references_are_aggregated_in_execution_order_and_deduplicated() -> None:
    source_tree = _tree(100, "source-tree")
    start = _node(source_tree, 101, "start", NodeType.START)
    rejected = _node(
        source_tree,
        102,
        "rejected",
        NodeType.CONDITION,
        condition_definition={"path": "input.value", "op": "lt", "value": 0},
    )
    link = _node(
        source_tree,
        103,
        "link",
        NodeType.LINK,
        link_target_tree_key="target-tree",
    )
    source_graph = _graph(
        source_tree,
        [start, rejected, link],
        [_edge(source_tree, 110, start, rejected, 1), _edge(source_tree, 111, start, link, 2)],
        [
            _reference(120, start, 1, "Start evidence"),
            _reference(121, rejected, 1, "Rejected evidence"),
            _reference(122, link, 1, "Link evidence"),
        ],
    )

    target_tree = _tree(200, "target-tree")
    target_start = _node(target_tree, 201, "target-start", NodeType.START)
    target_end = _node(target_tree, 202, "target-end", NodeType.END)
    end_reference = _reference(220, target_end, 1, "End evidence")
    target_graph = _graph(
        target_tree,
        [target_start, target_end],
        [_edge(target_tree, 210, target_start, target_end)],
        [
            _reference(221, target_start, 1, "Target start evidence"),
            end_reference,
        ],
    )
    duplicated_references = dict(target_graph.references_by_node_id)
    duplicated_references[target_end.id] = (end_reference, end_reference)
    target_graph = replace(
        target_graph,
        references_by_node_id=MappingProxyType(duplicated_references),
    )

    result = walk_tree(
        source_graph,
        {"value": 5},
        repository=InMemoryGraphRepository([target_graph]),
    )

    assert [(reference.tree_key, reference.node_key) for reference in result.references] == [
        ("source-tree", "start"),
        ("source-tree", "link"),
        ("target-tree", "target-start"),
        ("target-tree", "target-end"),
    ]
    assert "Rejected evidence" not in [reference.source_title for reference in result.references]
    end_result = result.references[-1]
    assert end_result.model_dump(mode="json") == {
        "tree_key": "target-tree",
        "node_key": "target-end",
        "reference_order": 1,
        "source_title": "End evidence",
        "section_path": ["section", "1"],
        "locator": "table",
        "locator_detail": "row 1",
        "printed_page_numbers": [10],
        "pdf_page_numbers": [20],
        "reference_note": "note",
    }


def test_cycle_detection_uses_tree_and_node_identity_across_links() -> None:
    source_tree = _tree(100, "source-tree")
    source_start = _node(source_tree, 101, "start", NodeType.START)
    to_target = _node(
        source_tree,
        102,
        "to-target",
        NodeType.LINK,
        link_target_tree_key="target-tree",
    )
    source_graph = _graph(
        source_tree,
        [source_start, to_target],
        [_edge(source_tree, 110, source_start, to_target)],
    )

    target_tree = _tree(200, "target-tree")
    target_start = _node(target_tree, 201, "start", NodeType.START)
    to_source = _node(
        target_tree,
        202,
        "to-source",
        NodeType.LINK,
        link_target_tree_key="source-tree",
        link_target_node_key="start",
    )
    target_graph = _graph(
        target_tree,
        [target_start, to_source],
        [_edge(target_tree, 210, target_start, to_source)],
    )

    with pytest.raises(TraversalCycleDetected) as exc_info:
        walk_tree(
            source_graph,
            {},
            repository=InMemoryGraphRepository([source_graph, target_graph]),
        )

    partial = exc_info.value.partial_run_state
    assert partial is not None
    assert _entered(partial.trace) == [
        ("source-tree", "start"),
        ("source-tree", "to-target"),
        ("target-tree", "start"),
        ("target-tree", "to-source"),
    ]


def test_global_step_limit_is_retained_after_link_transfer() -> None:
    source_tree = _tree(100, "source-tree")
    source_start = _node(source_tree, 101, "start", NodeType.START)
    link = _node(
        source_tree,
        102,
        "link",
        NodeType.LINK,
        link_target_tree_key="target-tree",
    )
    source_graph = _graph(
        source_tree,
        [source_start, link],
        [_edge(source_tree, 110, source_start, link)],
    )
    target_tree = _tree(200, "target-tree")
    target_start = _node(target_tree, 201, "target-start", NodeType.START)
    target_action = _node(target_tree, 202, "target-action", NodeType.ACTION)
    target_graph = _graph(
        target_tree,
        [target_start, target_action],
        [_edge(target_tree, 210, target_start, target_action)],
    )

    with pytest.raises(TraversalLimitExceeded) as exc_info:
        walk_tree(
            source_graph,
            {},
            repository=InMemoryGraphRepository([target_graph]),
            max_steps=3,
        )

    partial = exc_info.value.partial_run_state
    assert partial is not None
    assert [entry.step for entry in partial.trace] == [1, 2, 3]
    assert _entered(partial.trace) == [
        ("source-tree", "start"),
        ("source-tree", "link"),
    ]
