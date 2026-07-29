"""Validated construction of immutable decision-tree graphs."""

from collections.abc import Sequence
from types import MappingProxyType
from uuid import UUID

from cdss.domain.decision_tree.contracts import NodeType
from cdss.domain.decision_tree.errors import InvalidStartNode
from cdss.domain.decision_tree.graph import (
    EdgeDefinition,
    NodeDefinition,
    SourceReferenceDefinition,
    TreeDefinition,
    TreeGraph,
)
from cdss.domain.decision_tree.graph_freezing import (
    freeze_node,
    freeze_reference,
    invalid_structure,
    validate_edge_tree_ownership,
)


class GraphBuilder:
    @classmethod
    def build(
        cls,
        *,
        tree: TreeDefinition,
        nodes: Sequence[NodeDefinition],
        edges: Sequence[EdgeDefinition],
        references: Sequence[SourceReferenceDefinition],
    ) -> TreeGraph:
        nodes_by_id: dict[UUID, NodeDefinition] = {}
        nodes_by_key: dict[str, NodeDefinition] = {}

        for source_node in nodes:
            node = freeze_node(tree, source_node)
            if node.tree_id != tree.id:
                raise invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="node_belongs_to_another_tree",
                    node_id=str(node.id),
                )
            if node.id in nodes_by_id:
                raise invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="duplicate_node_id",
                    node_id=str(node.id),
                )
            if node.node_key in nodes_by_key:
                raise invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="duplicate_node_key",
                )
            nodes_by_id[node.id] = node
            nodes_by_key[node.node_key] = node

        start_nodes = [node for node in nodes_by_id.values() if node.node_type is NodeType.START]
        if len(start_nodes) != 1:
            raise InvalidStartNode(
                tree_key=tree.tree_key,
                details={"start_node_count": len(start_nodes)},
            )

        outgoing: dict[UUID, list[EdgeDefinition]] = {node_id: [] for node_id in nodes_by_id}
        edge_ids: set[UUID] = set()
        edge_targets: set[tuple[UUID, UUID]] = set()
        traversal_orders: set[tuple[UUID, int]] = set()

        for edge in edges:
            validate_edge_tree_ownership(tree, edge)
            from_node = nodes_by_id.get(edge.from_node_id)
            to_node = nodes_by_id.get(edge.to_node_id)
            if from_node is None or to_node is None:
                missing_ids = [
                    str(node_id)
                    for node_id, node in (
                        (edge.from_node_id, from_node),
                        (edge.to_node_id, to_node),
                    )
                    if node is None
                ]
                raise invalid_structure(
                    tree,
                    node_key=from_node.node_key if from_node is not None else None,
                    reason="edge_references_missing_node",
                    edge_id=str(edge.id),
                    missing_node_ids=missing_ids,
                )
            if from_node.node_type is NodeType.GLOBAL or to_node.node_type is NodeType.GLOBAL:
                raise invalid_structure(
                    tree,
                    node_key=from_node.node_key,
                    reason="global_node_has_internal_edge",
                    edge_id=str(edge.id),
                )
            if edge.id in edge_ids:
                raise invalid_structure(
                    tree,
                    node_key=from_node.node_key,
                    reason="duplicate_edge_id",
                    edge_id=str(edge.id),
                )
            edge_target = (edge.from_node_id, edge.to_node_id)
            if edge_target in edge_targets:
                raise invalid_structure(
                    tree,
                    node_key=from_node.node_key,
                    reason="duplicate_edge_target",
                    edge_id=str(edge.id),
                )
            traversal_order = (edge.from_node_id, edge.traversal_order)
            if traversal_order in traversal_orders:
                raise invalid_structure(
                    tree,
                    node_key=from_node.node_key,
                    reason="duplicate_traversal_order",
                    traversal_order=edge.traversal_order,
                )
            edge_ids.add(edge.id)
            edge_targets.add(edge_target)
            traversal_orders.add(traversal_order)
            outgoing[edge.from_node_id].append(edge)

        references_by_node: dict[UUID, list[SourceReferenceDefinition]] = {
            node_id: [] for node_id in nodes_by_id
        }
        reference_ids: set[UUID] = set()
        reference_orders: set[tuple[UUID, int]] = set()
        for source_reference in references:
            try:
                reference = freeze_reference(source_reference)
            except TypeError as exc:
                raise invalid_structure(
                    tree,
                    reason="invalid_reference_json",
                    reference_id=str(source_reference.id),
                ) from exc
            node = nodes_by_id.get(reference.node_id)
            if node is None:
                raise invalid_structure(
                    tree,
                    reason="reference_points_to_missing_node",
                    reference_id=str(reference.id),
                    node_id=str(reference.node_id),
                )
            if reference.id in reference_ids:
                raise invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="duplicate_reference_id",
                    reference_id=str(reference.id),
                )
            reference_order = (reference.node_id, reference.reference_order)
            if reference_order in reference_orders:
                raise invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="duplicate_reference_order",
                    reference_order=reference.reference_order,
                )
            reference_ids.add(reference.id)
            reference_orders.add(reference_order)
            references_by_node[reference.node_id].append(reference)

        sorted_outgoing = {
            node_id: tuple(sorted(node_edges, key=lambda edge: edge.traversal_order))
            for node_id, node_edges in outgoing.items()
        }
        sorted_references = {
            node_id: tuple(sorted(node_references, key=lambda reference: reference.reference_order))
            for node_id, node_references in references_by_node.items()
        }
        global_nodes = tuple(
            sorted(
                (node for node in nodes_by_id.values() if node.node_type is NodeType.GLOBAL),
                key=lambda node: (node.display_order, node.node_key),
            )
        )

        return TreeGraph(
            tree=tree,
            start_node=start_nodes[0],
            nodes_by_id=MappingProxyType(nodes_by_id),
            nodes_by_key=MappingProxyType(nodes_by_key),
            outgoing_edges_by_node_id=MappingProxyType(sorted_outgoing),
            references_by_node_id=MappingProxyType(sorted_references),
            global_nodes=global_nodes,
        )
