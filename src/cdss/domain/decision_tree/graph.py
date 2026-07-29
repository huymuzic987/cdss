"""Immutable in-memory representation of a loaded decision tree."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from cdss.domain.decision_tree.contracts import NodeType


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
        from cdss.domain.decision_tree.graph_builder import GraphBuilder

        return GraphBuilder.build(
            tree=tree,
            nodes=nodes,
            edges=edges,
            references=references,
        )


class TreeGraphRepository(Protocol):
    def get_tree(self, tree_key: str) -> TreeGraph: ...

    def list_trees(self) -> Sequence[TreeDefinition]: ...
