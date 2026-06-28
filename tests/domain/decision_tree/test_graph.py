"""Pure unit tests for immutable decision-tree graphs."""

from typing import Any
from uuid import UUID

import pytest

from cdss.domain.decision_tree import (
    EdgeDefinition,
    InvalidStartNode,
    InvalidTreeStructure,
    NodeDefinition,
    NodeType,
    SourceReferenceDefinition,
    TreeDefinition,
    TreeGraph,
)

TREE_ID = UUID(int=1)
OTHER_TREE_ID = UUID(int=2)
TREE = TreeDefinition(
    id=TREE_ID,
    tree_key="test-tree",
    name_en="Test tree",
    name_vi="Cay thu nghiem",
)


def _node(
    serial: int,
    node_key: str,
    node_type: NodeType,
    *,
    tree_id: UUID = TREE_ID,
    **values: Any,
) -> NodeDefinition:
    return NodeDefinition(
        id=UUID(int=serial),
        tree_id=tree_id,
        node_key=node_key,
        node_type=node_type,
        text_en=node_key,
        text_vi=node_key,
        **values,
    )


def _edge(
    serial: int,
    from_node: NodeDefinition,
    to_node: NodeDefinition,
    traversal_order: int,
    *,
    from_tree_id: UUID = TREE_ID,
    to_tree_id: UUID = TREE_ID,
) -> EdgeDefinition:
    return EdgeDefinition(
        id=UUID(int=serial),
        from_node_id=from_node.id,
        to_node_id=to_node.id,
        traversal_order=traversal_order,
        from_tree_id=from_tree_id,
        to_tree_id=to_tree_id,
    )


def test_builds_valid_graph_with_complete_indexes() -> None:
    start = _node(10, "start", NodeType.START)
    action = _node(11, "action", NodeType.ACTION, action_payload={"kind": "monitor"})
    edge = _edge(20, start, action, 1)
    references = [
        SourceReferenceDefinition(
            id=UUID(int=31),
            node_id=action.id,
            source_title="Guideline B",
            section_path=["2"],
            reference_order=2,
        ),
        SourceReferenceDefinition(
            id=UUID(int=30),
            node_id=action.id,
            source_title="Guideline A",
            section_path=["1"],
            reference_order=1,
        ),
    ]

    graph = TreeGraph.build(
        tree=TREE,
        nodes=[start, action],
        edges=[edge],
        references=references,
    )

    assert graph.tree is TREE
    assert graph.start_node.node_key == "start"
    assert graph.nodes_by_id[action.id].node_key == "action"
    assert graph.nodes_by_key["start"].id == start.id
    assert graph.outgoing_edges_by_node_id[start.id] == (edge,)
    assert graph.outgoing_edges_by_node_id[action.id] == ()
    assert [reference.reference_order for reference in graph.references_by_node_id[action.id]] == [
        1,
        2,
    ]
    assert graph.references_by_node_id[start.id] == ()
    with pytest.raises(TypeError):
        graph.nodes_by_id[action.id] = start  # type: ignore[index]


@pytest.mark.parametrize(
    "nodes",
    [
        [_node(11, "action", NodeType.ACTION)],
        [
            _node(10, "start-a", NodeType.START),
            _node(11, "start-b", NodeType.START),
        ],
    ],
)
def test_requires_exactly_one_start_node(nodes: list[NodeDefinition]) -> None:
    with pytest.raises(InvalidStartNode):
        TreeGraph.build(tree=TREE, nodes=nodes, edges=[], references=[])


def test_orders_outgoing_edges_by_traversal_order() -> None:
    start = _node(10, "start", NodeType.START)
    first = _node(11, "first", NodeType.ACTION)
    second = _node(12, "second", NodeType.ACTION)
    later_edge = _edge(20, start, second, 20)
    first_edge = _edge(21, start, first, 10)

    graph = TreeGraph.build(
        tree=TREE,
        nodes=[start, first, second],
        edges=[later_edge, first_edge],
        references=[],
    )

    assert graph.outgoing_edges_by_node_id[start.id] == (first_edge, later_edge)


def test_global_nodes_are_ordered_metadata() -> None:
    start = _node(10, "start", NodeType.START)
    later_global = _node(
        11,
        "global-later",
        NodeType.GLOBAL,
        display_order=20,
        global_config={"unit": "mmHg"},
    )
    first_global = _node(
        12,
        "global-first",
        NodeType.GLOBAL,
        display_order=10,
        global_config={"locale": "vi"},
    )

    graph = TreeGraph.build(
        tree=TREE,
        nodes=[start, later_global, first_global],
        edges=[],
        references=[],
    )

    assert [node.node_key for node in graph.global_nodes] == [
        "global-first",
        "global-later",
    ]
    assert graph.outgoing_edges_by_node_id[first_global.id] == ()


def test_rejects_cross_tree_edge() -> None:
    start = _node(10, "start", NodeType.START)
    action = _node(11, "action", NodeType.ACTION)
    edge = _edge(20, start, action, 1, to_tree_id=OTHER_TREE_ID)

    with pytest.raises(InvalidTreeStructure) as exc_info:
        TreeGraph.build(
            tree=TREE,
            nodes=[start, action],
            edges=[edge],
            references=[],
        )

    assert exc_info.value.details["reason"] == "cross_tree_edge"


def test_rejects_edge_referencing_missing_node() -> None:
    start = _node(10, "start", NodeType.START)
    missing_node_id = UUID(int=99)
    edge = EdgeDefinition(
        id=UUID(int=20),
        from_node_id=start.id,
        to_node_id=missing_node_id,
        traversal_order=1,
        from_tree_id=TREE_ID,
        to_tree_id=TREE_ID,
    )

    with pytest.raises(InvalidTreeStructure) as exc_info:
        TreeGraph.build(tree=TREE, nodes=[start], edges=[edge], references=[])

    assert exc_info.value.details["reason"] == "edge_references_missing_node"
    assert exc_info.value.details["missing_node_ids"] == [str(missing_node_id)]
