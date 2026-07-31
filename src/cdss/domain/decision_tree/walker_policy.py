"""Small traversal policies kept outside the main walker implementation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from uuid import UUID

from cdss.domain.decision_tree.contracts import NodeType
from cdss.domain.decision_tree.graph import EdgeDefinition, NodeDefinition

_CONTINUATION_TREES = frozenset({"essential-treatment-strategy", "optimal-treatment-strategy"})
_CONTINUATION_NODES = frozenset(
    {
        ("hypertension-in-pregnancy", "T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM"),
        ("hypertension-in-pregnancy", "T12_C_IMMEDIATE_TARGET"),
        ("resistant-hypertension", "T13_A_CHECK_MRA"),
        ("resistant-hypertension", "T13_A_CHECK_SPIRONOLACTONE"),
        ("hypertensive-emergency", "T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN"),
    }
)


def action_may_continue(
    tree_key: str,
    node_key: str,
    edges: Iterable[EdgeDefinition],
    nodes: Mapping[UUID, NodeDefinition],
) -> bool:
    edges = tuple(edges)
    if not edges:
        return False
    if (tree_key, node_key) in _CONTINUATION_NODES:
        return True
    return tree_key in _CONTINUATION_TREES and all(
        nodes[edge.to_node_id].node_type is NodeType.LINK for edge in edges
    )
