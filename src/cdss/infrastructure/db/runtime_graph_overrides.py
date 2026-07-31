"""Small, explicit runtime graph compatibility overrides.

The authoritative SQL seed is intentionally left unchanged. These overrides
adapt legacy persisted graph relationships when loading an immutable graph so
the evaluator, graph API, and FHIR exports all observe the same effective tree.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import NAMESPACE_URL, uuid5

from cdss.domain.decision_tree.errors import InvalidTreeStructure
from cdss.domain.decision_tree.graph import (
    EdgeDefinition,
    NodeDefinition,
    TreeDefinition,
)

_NODE_OVERRIDES = {
    "hypertension-diagnosis": {
        "T1_C_IS_PREGNANT": {
            "text_en": "Patient is pregnant or in pregnancy-related postpartum follow-up",
            "text_vi": ("Bệnh nhân đang mang thai hoặc đang theo dõi hậu sản liên quan thai kỳ"),
            "condition_definition": {
                "any": [
                    {"op": "eq", "path": "input.is_pregnant", "value": True},
                    {"op": "eq", "path": "input.is_postpartum", "value": True},
                ]
            },
        },
        "T1_C_IS_NOT_PREGNANT": {
            "text_en": (
                "Patient is neither pregnant nor in pregnancy-related postpartum follow-up"
            ),
            "text_vi": "Bệnh nhân không mang thai và không trong giai đoạn theo dõi hậu sản",
            "condition_definition": {
                "all": [
                    {"op": "eq", "path": "input.is_pregnant", "value": False},
                    {"op": "eq", "path": "input.is_postpartum", "value": False},
                ]
            },
        },
    }
}

_EDGE_ORDER_OVERRIDES = {
    "hypertension-in-pregnancy": {
        "T12_START_PREGNANCY_HTN_SEQUENCE": (
            "T12_C_HOME_BP_HIGH",
            "T12_C_CLINIC_BP_HIGH",
            "T12_C_CLINIC_BP_NORMAL",
        ),
        "T12_C_HOME_BP_HIGH": (
            "T12_C_CHRONIC_HTN",
            "T12_C_SEVERE_SIGNS",
            "T12_C_HELLP_SIGNS",
            "T12_C_PREECLAMPSIA_PROTEINURIA",
            "T12_C_PREECLAMPSIA_RISK_FACTOR",
            "T12_C_GESTATIONAL_HTN",
        ),
        "T12_C_CLINIC_BP_HIGH": (
            "T12_C_CHRONIC_HTN",
            "T12_C_SEVERE_SIGNS",
            "T12_C_HELLP_SIGNS",
            "T12_C_PREECLAMPSIA_PROTEINURIA",
            "T12_C_PREECLAMPSIA_RISK_FACTOR",
            "T12_C_GESTATIONAL_HTN",
        ),
    }
}


def apply_runtime_graph_overrides(
    tree: TreeDefinition,
    nodes: list[NodeDefinition],
    edges: list[EdgeDefinition],
) -> tuple[list[NodeDefinition], list[EdgeDefinition]]:
    """Return the effective graph while preserving all persisted rows."""

    nodes = _apply_node_overrides(tree, nodes)
    edges = _apply_edge_overrides(tree, nodes, edges)
    return nodes, edges


def _apply_node_overrides(
    tree: TreeDefinition,
    nodes: list[NodeDefinition],
) -> list[NodeDefinition]:
    overrides = _NODE_OVERRIDES.get(tree.tree_key)
    if not overrides:
        return nodes
    available = {node.node_key for node in nodes}
    missing = set(overrides) - available
    if missing:
        _invalid_override(tree, missing)
    return [
        replace(node, **overrides[node.node_key]) if node.node_key in overrides else node
        for node in nodes
    ]


def _apply_edge_overrides(
    tree: TreeDefinition,
    nodes: list[NodeDefinition],
    edges: list[EdgeDefinition],
) -> list[EdgeDefinition]:
    overrides = _EDGE_ORDER_OVERRIDES.get(tree.tree_key)
    if not overrides:
        return edges

    nodes_by_key = {node.node_key: node for node in nodes}
    required = set(overrides)
    required.update(target for targets in overrides.values() for target in targets)
    missing = required - set(nodes_by_key)
    if missing:
        _invalid_override(tree, missing)

    source_ids = {nodes_by_key[source].id for source in overrides}
    existing = {(edge.from_node_id, edge.to_node_id): edge for edge in edges}
    effective = [edge for edge in edges if edge.from_node_id not in source_ids]

    for source_key, target_keys in overrides.items():
        source = nodes_by_key[source_key]
        for traversal_order, target_key in enumerate(target_keys, start=1):
            target = nodes_by_key[target_key]
            effective.append(
                existing.get(
                    (source.id, target.id),
                    EdgeDefinition(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"cdss-runtime-edge:{tree.tree_key}:{source_key}->{target_key}",
                        ),
                        from_node_id=source.id,
                        to_node_id=target.id,
                        traversal_order=traversal_order,
                        from_tree_id=tree.id,
                        to_tree_id=tree.id,
                    ),
                )
            )
            if effective[-1].traversal_order != traversal_order:
                effective[-1] = replace(
                    effective[-1],
                    traversal_order=traversal_order,
                )
    return effective


def _invalid_override(tree: TreeDefinition, missing: set[str]) -> None:
    raise InvalidTreeStructure(
        tree_key=tree.tree_key,
        details={
            "reason": "runtime_graph_override_node_missing",
            "missing_node_keys": sorted(missing),
        },
    )
