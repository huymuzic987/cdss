"""Schemas for read-only tree-graph inspection (frontend visualization)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from cdss.api.schemas.evaluation import ApiModel
from cdss.domain.decision_tree import JsonObject, JsonValue, NodeType, TreeGraph
from cdss.domain.decision_tree.contracts import copy_json_value


def _copy_json_object(value: Mapping[str, Any] | None) -> JsonObject | None:
    if value is None:
        return None
    return cast(JsonObject, copy_json_value(value))


class TreeSummary(ApiModel):
    tree_key: str
    name_en: str
    name_vi: str


class TreeGraphNode(ApiModel):
    node_key: str
    node_type: NodeType
    text_en: str
    text_vi: str
    condition_definition: JsonObject | None = None
    context_patch: JsonObject | None = None
    action_payload: JsonObject | None = None
    link_target_tree_key: str | None = None
    link_target_node_key: str | None = None
    display_order: int


class TreeGraphEdge(ApiModel):
    from_node_key: str
    to_node_key: str
    traversal_order: int


class TreeGraphSourceReference(ApiModel):
    node_key: str
    source_title: str
    section_path: JsonValue
    reference_order: int
    locator: str | None = None
    locator_detail: str | None = None
    reference_note: str | None = None


class TreeGraphGlobalNode(ApiModel):
    node_key: str
    text_en: str
    text_vi: str
    global_config: JsonObject | None = None
    display_order: int


class TreeGraphResponse(ApiModel):
    tree: TreeSummary
    start_node_key: str
    nodes: list[TreeGraphNode]
    edges: list[TreeGraphEdge]
    global_nodes: list[TreeGraphGlobalNode]
    references: list[TreeGraphSourceReference]

    @classmethod
    def from_graph(cls, graph: TreeGraph) -> TreeGraphResponse:
        nodes: list[TreeGraphNode] = []
        edges: list[TreeGraphEdge] = []
        global_nodes: list[TreeGraphGlobalNode] = []
        references: list[TreeGraphSourceReference] = []

        for node in graph.nodes_by_id.values():
            if node.node_type is NodeType.GLOBAL:
                global_nodes.append(
                    TreeGraphGlobalNode(
                        node_key=node.node_key,
                        text_en=node.text_en,
                        text_vi=node.text_vi,
                        global_config=_copy_json_object(node.global_config),
                        display_order=node.display_order,
                    )
                )
                continue

            nodes.append(
                TreeGraphNode(
                    node_key=node.node_key,
                    node_type=node.node_type,
                    text_en=node.text_en,
                    text_vi=node.text_vi,
                    condition_definition=_copy_json_object(node.condition_definition),
                    context_patch=_copy_json_object(node.context_patch),
                    action_payload=_copy_json_object(node.action_payload),
                    link_target_tree_key=node.link_target_tree_key,
                    link_target_node_key=node.link_target_node_key,
                    display_order=node.display_order,
                )
            )

            for edge in graph.outgoing_edges_by_node_id.get(node.id, ()):
                to_node = graph.nodes_by_id[edge.to_node_id]
                edges.append(
                    TreeGraphEdge(
                        from_node_key=node.node_key,
                        to_node_key=to_node.node_key,
                        traversal_order=edge.traversal_order,
                    )
                )

            references.extend(
                TreeGraphSourceReference(
                    node_key=node.node_key,
                    source_title=reference.source_title,
                    section_path=copy_json_value(reference.section_path),
                    reference_order=reference.reference_order,
                    locator=reference.locator,
                    locator_detail=reference.locator_detail,
                    reference_note=reference.reference_note,
                )
                for reference in graph.references_by_node_id.get(node.id, ())
            )

        return cls(
            tree=TreeSummary(
                tree_key=graph.tree.tree_key,
                name_en=graph.tree.name_en,
                name_vi=graph.tree.name_vi,
            ),
            start_node_key=graph.start_node.node_key,
            nodes=nodes,
            edges=edges,
            global_nodes=global_nodes,
            references=references,
        )
