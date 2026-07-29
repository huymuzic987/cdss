"""Public coordinator for structural decision-tree validation."""

from collections.abc import Set

from cdss.domain.decision_tree.contracts import NodeType
from cdss.domain.decision_tree.errors import InvalidStartNode
from cdss.domain.decision_tree.graph import TreeGraph
from cdss.domain.decision_tree.validation_edges import validate_edges
from cdss.domain.decision_tree.validation_errors import structure_error
from cdss.domain.decision_tree.validation_semantics import validate_node_semantics
from cdss.domain.decision_tree.validation_topology import (
    validate_link_targets,
    validate_no_cycles,
    validate_reachability,
)
from cdss.domain.decision_tree.validation_types import (
    TreeValidationResult,
    TreeValidationWarning,
)

__all__ = ["TreeValidationResult", "TreeValidationWarning", "validate_tree_graph"]


def validate_tree_graph(
    graph: TreeGraph,
    *,
    available_tree_keys: Set[str] | None = None,
    strict_link_targets: bool = False,
) -> TreeValidationResult:
    """Validate one graph and report unavailable external links as warnings."""

    tree = graph.tree
    nodes = sorted(
        graph.nodes_by_id.values(),
        key=lambda node: (node.display_order, node.node_key, str(node.id)),
    )
    for node in nodes:
        if node.tree_id != tree.id:
            raise structure_error(
                graph,
                node=node,
                reason="node_belongs_to_another_tree",
                node_id=str(node.id),
            )

    start_nodes = [node for node in nodes if node.node_type is NodeType.START]
    if len(start_nodes) != 1 or graph.start_node.id != start_nodes[0].id:
        raise InvalidStartNode(
            tree_key=tree.tree_key,
            details={"start_node_count": len(start_nodes)},
        )

    adjacency, outgoing_counts = validate_edges(graph)
    validate_node_semantics(graph, nodes, outgoing_counts)
    validate_no_cycles(graph, nodes, adjacency)
    validate_reachability(graph, nodes, adjacency, start_nodes[0].id)

    warnings = validate_link_targets(
        graph,
        nodes,
        available_tree_keys=available_tree_keys,
        strict_link_targets=strict_link_targets,
    )
    return TreeValidationResult(tree_key=tree.tree_key, warnings=warnings)
