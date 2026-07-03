"""Immutable in-memory representation of a loaded decision tree."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Protocol
from uuid import UUID

from cdss.domain.decision_tree.contracts import FrozenJsonObject, NodeType
from cdss.domain.decision_tree.errors import InvalidStartNode, InvalidTreeStructure


@dataclass(frozen=True, slots=True)
class TreeDefinition:
    id: UUID
    tree_key: str
    name_en: str
    name_vi: str


@dataclass(frozen=True, slots=True)
class NodeDefinition:
    id: UUID
    tree_id: UUID
    node_key: str
    node_type: NodeType
    text_en: str
    text_vi: str
    condition_definition: Mapping[str, Any] | None = None
    context_patch: Mapping[str, Any] | None = None
    action_payload: Mapping[str, Any] | None = None
    global_config: Mapping[str, Any] | None = None
    link_target_tree_key: str | None = None
    link_target_node_key: str | None = None
    display_order: int = 0


@dataclass(frozen=True, slots=True)
class EdgeDefinition:
    id: UUID
    from_node_id: UUID
    to_node_id: UUID
    traversal_order: int
    from_tree_id: UUID | None = None
    to_tree_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class SourceReferenceDefinition:
    id: UUID
    node_id: UUID
    source_title: str
    section_path: Any
    reference_order: int
    locator: str | None = None
    locator_detail: str | None = None
    printed_page_numbers: tuple[int, ...] | None = None
    pdf_page_numbers: tuple[int, ...] | None = None
    reference_note: str | None = None


@dataclass(frozen=True, slots=True)
class TreeGraph:
    tree: TreeDefinition
    start_node: NodeDefinition
    nodes_by_id: Mapping[UUID, NodeDefinition]
    nodes_by_key: Mapping[str, NodeDefinition]
    outgoing_edges_by_node_id: Mapping[UUID, tuple[EdgeDefinition, ...]]
    references_by_node_id: Mapping[UUID, tuple[SourceReferenceDefinition, ...]]
    global_nodes: tuple[NodeDefinition, ...]

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
            node = _freeze_node(tree, source_node)
            if node.tree_id != tree.id:
                raise _invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="node_belongs_to_another_tree",
                    node_id=str(node.id),
                )
            if node.id in nodes_by_id:
                raise _invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="duplicate_node_id",
                    node_id=str(node.id),
                )
            if node.node_key in nodes_by_key:
                raise _invalid_structure(
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
            _validate_edge_tree_ownership(tree, edge)
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
                raise _invalid_structure(
                    tree,
                    node_key=from_node.node_key if from_node is not None else None,
                    reason="edge_references_missing_node",
                    edge_id=str(edge.id),
                    missing_node_ids=missing_ids,
                )
            if from_node.node_type is NodeType.GLOBAL or to_node.node_type is NodeType.GLOBAL:
                raise _invalid_structure(
                    tree,
                    node_key=from_node.node_key,
                    reason="global_node_has_internal_edge",
                    edge_id=str(edge.id),
                )
            if edge.id in edge_ids:
                raise _invalid_structure(
                    tree,
                    node_key=from_node.node_key,
                    reason="duplicate_edge_id",
                    edge_id=str(edge.id),
                )
            edge_target = (edge.from_node_id, edge.to_node_id)
            if edge_target in edge_targets:
                raise _invalid_structure(
                    tree,
                    node_key=from_node.node_key,
                    reason="duplicate_edge_target",
                    edge_id=str(edge.id),
                )
            traversal_order = (edge.from_node_id, edge.traversal_order)
            if traversal_order in traversal_orders:
                raise _invalid_structure(
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
                reference = _freeze_reference(source_reference)
            except TypeError as exc:
                raise _invalid_structure(
                    tree,
                    reason="invalid_reference_json",
                    reference_id=str(source_reference.id),
                ) from exc
            node = nodes_by_id.get(reference.node_id)
            if node is None:
                raise _invalid_structure(
                    tree,
                    reason="reference_points_to_missing_node",
                    reference_id=str(reference.id),
                    node_id=str(reference.node_id),
                )
            if reference.id in reference_ids:
                raise _invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="duplicate_reference_id",
                    reference_id=str(reference.id),
                )
            reference_order = (reference.node_id, reference.reference_order)
            if reference_order in reference_orders:
                raise _invalid_structure(
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

        return cls(
            tree=tree,
            start_node=start_nodes[0],
            nodes_by_id=MappingProxyType(nodes_by_id),
            nodes_by_key=MappingProxyType(nodes_by_key),
            outgoing_edges_by_node_id=MappingProxyType(sorted_outgoing),
            references_by_node_id=MappingProxyType(sorted_references),
            global_nodes=global_nodes,
        )


class TreeGraphRepository(Protocol):
    """Loading boundary used by traversal and replaceable by in-memory fakes."""

    def get_tree(self, tree_key: str) -> TreeGraph:
        """Load and validate one complete tree graph."""
        ...

    def list_trees(self) -> Sequence[TreeDefinition]:
        """List every tree's identity without loading its full graph."""
        ...


def _freeze_node(tree: TreeDefinition, node: NodeDefinition) -> NodeDefinition:
    frozen_values: dict[str, FrozenJsonObject | None] = {}
    for field_name in (
        "condition_definition",
        "context_patch",
        "action_payload",
        "global_config",
    ):
        value = getattr(node, field_name)
        if value is None or isinstance(value, FrozenJsonObject):
            frozen_values[field_name] = value
        elif isinstance(value, Mapping):
            try:
                frozen_values[field_name] = FrozenJsonObject(value)
            except TypeError as exc:
                raise _invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="invalid_node_json",
                    field=field_name,
                ) from exc
        else:
            raise _invalid_structure(
                tree,
                node_key=node.node_key,
                reason="invalid_node_json",
                field=field_name,
            )
    return replace(node, **frozen_values)


def _freeze_reference(reference: SourceReferenceDefinition) -> SourceReferenceDefinition:
    return replace(
        reference,
        section_path=_freeze_json_value(reference.section_path),
        printed_page_numbers=(
            tuple(reference.printed_page_numbers)
            if reference.printed_page_numbers is not None
            else None
        ),
        pdf_page_numbers=(
            tuple(reference.pdf_page_numbers) if reference.pdf_page_numbers is not None else None
        ),
    )


def _freeze_json_value(value: Any) -> Any:
    return FrozenJsonObject({"value": value})["value"]


def _validate_edge_tree_ownership(tree: TreeDefinition, edge: EdgeDefinition) -> None:
    endpoint_tree_ids = (edge.from_tree_id, edge.to_tree_id)
    if any(tree_id is not None and tree_id != tree.id for tree_id in endpoint_tree_ids):
        raise _invalid_structure(
            tree,
            reason="cross_tree_edge",
            edge_id=str(edge.id),
            from_tree_id=str(edge.from_tree_id) if edge.from_tree_id is not None else None,
            to_tree_id=str(edge.to_tree_id) if edge.to_tree_id is not None else None,
        )


def _invalid_structure(
    tree: TreeDefinition,
    *,
    reason: str,
    node_key: str | None = None,
    **details: Any,
) -> InvalidTreeStructure:
    return InvalidTreeStructure(
        tree_key=tree.tree_key,
        node_key=node_key,
        details={"reason": reason, **details},
    )
