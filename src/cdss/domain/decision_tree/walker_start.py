"""Resolve an optional resumable entry point for tree traversal."""

from cdss.domain.decision_tree.contracts import NodeType, RunState
from cdss.domain.decision_tree.errors import InvalidTreeStructure
from cdss.domain.decision_tree.graph import NodeDefinition, TreeGraph


def resolve_start_node(
    graph: TreeGraph,
    start_node_key: str | None,
    run_state: RunState,
) -> NodeDefinition:
    if start_node_key is None:
        return graph.start_node
    start_node = graph.nodes_by_key.get(start_node_key)
    if start_node is None:
        raise InvalidTreeStructure(
            tree_key=graph.tree.tree_key,
            node_key=start_node_key,
            details={"reason": "requested_start_node_missing"},
            partial_run_state=run_state,
        )
    if start_node.node_type is NodeType.GLOBAL:
        raise InvalidTreeStructure(
            tree_key=graph.tree.tree_key,
            node_key=start_node_key,
            details={"reason": "requested_start_node_is_global"},
            partial_run_state=run_state,
        )
    return start_node
