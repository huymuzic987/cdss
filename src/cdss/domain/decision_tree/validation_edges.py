"""Edge indexing and ownership validation."""

from uuid import UUID

from cdss.domain.decision_tree.contracts import NodeType
from cdss.domain.decision_tree.graph import EdgeDefinition, TreeGraph
from cdss.domain.decision_tree.validation_errors import structure_error


def validate_edges(
    graph: TreeGraph,
) -> tuple[dict[UUID, tuple[UUID, ...]], dict[UUID, int]]:
    nodes_by_id = graph.nodes_by_id
    adjacency_lists: dict[UUID, list[UUID]] = {node_id: [] for node_id in nodes_by_id}
    outgoing_counts: dict[UUID, int] = {node_id: 0 for node_id in nodes_by_id}
    edge_ids: set[UUID] = set()
    edge_targets: set[tuple[UUID, UUID]] = set()
    traversal_orders: set[tuple[UUID, int]] = set()

    for bucket_node_id, bucket in graph.outgoing_edges_by_node_id.items():
        if bucket_node_id not in nodes_by_id:
            raise structure_error(
                graph,
                reason="outgoing_edge_bucket_has_missing_source",
                node_id=str(bucket_node_id),
            )
        for edge in bucket:
            from_node = nodes_by_id.get(edge.from_node_id)
            to_node = nodes_by_id.get(edge.to_node_id)
            if edge.from_node_id != bucket_node_id:
                raise structure_error(
                    graph,
                    node=from_node,
                    reason="edge_stored_under_wrong_source",
                    edge_id=str(edge.id),
                )
            if edge_crosses_tree(graph, edge) or from_node is None or to_node is None:
                raise structure_error(
                    graph,
                    node=from_node,
                    reason="cross_tree_or_missing_edge_endpoint",
                    edge_id=str(edge.id),
                    from_node_id=str(edge.from_node_id),
                    to_node_id=str(edge.to_node_id),
                )
            if from_node.node_type is NodeType.GLOBAL or to_node.node_type is NodeType.GLOBAL:
                raise structure_error(
                    graph,
                    node=from_node,
                    reason="global_node_has_internal_edge",
                    edge_id=str(edge.id),
                )
            if edge.id in edge_ids:
                raise structure_error(
                    graph,
                    node=from_node,
                    reason="duplicate_edge_id",
                    edge_id=str(edge.id),
                )
            edge_target = (edge.from_node_id, edge.to_node_id)
            if edge_target in edge_targets:
                raise structure_error(
                    graph,
                    node=from_node,
                    reason="duplicate_edge_target",
                    edge_id=str(edge.id),
                )
            traversal_order = (edge.from_node_id, edge.traversal_order)
            if traversal_order in traversal_orders:
                raise structure_error(
                    graph,
                    node=from_node,
                    reason="duplicate_outgoing_traversal_order",
                    traversal_order=edge.traversal_order,
                )

            edge_ids.add(edge.id)
            edge_targets.add(edge_target)
            traversal_orders.add(traversal_order)
            adjacency_lists[edge.from_node_id].append(edge.to_node_id)
            outgoing_counts[edge.from_node_id] += 1

    adjacency = {node_id: tuple(targets) for node_id, targets in adjacency_lists.items()}
    return adjacency, outgoing_counts


def edge_crosses_tree(graph: TreeGraph, edge: EdgeDefinition) -> bool:
    tree_id = graph.tree.id
    endpoint_tree_ids = (edge.from_tree_id, edge.to_tree_id)
    if any(value is not None and value != tree_id for value in endpoint_tree_ids):
        return True
    from_node = graph.nodes_by_id.get(edge.from_node_id)
    to_node = graph.nodes_by_id.get(edge.to_node_id)
    return any(node is not None and node.tree_id != tree_id for node in (from_node, to_node))
