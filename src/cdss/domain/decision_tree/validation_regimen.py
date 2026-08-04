"""Validation for explicit medication-regimen inference payloads."""

import re
from collections.abc import Mapping

from cdss.domain.decision_tree.contracts import NodeType
from cdss.domain.decision_tree.graph import NodeDefinition, TreeGraph
from cdss.domain.decision_tree.validation_errors import structure_error

_KEY_OPERATION = re.compile(r"^T\d+_INFERENCE_([A-Z]+)_")
_OPERATIONS = frozenset(
    {
        "START",
        "ADD",
        "COMBINE",
        "SELECT",
        "ADJUST",
        "CHANGE",
        "ESCALATE",
        "REDUCE",
        "STOP",
        "KEEP",
        "MAINTAIN",
        "MONITOR",
        "AVOID",
        "RESTORE",
    }
)


def validate_regimen_update(graph: TreeGraph, node: NodeDefinition) -> None:
    """Require explicit regimen payloads to agree with their inference keys."""

    if node.node_type is not NodeType.INFERENCE:
        return
    payload = node.action_payload
    if not isinstance(payload, Mapping):
        return
    update = payload.get("regimen_update")
    if not isinstance(update, Mapping):
        return
    match = _KEY_OPERATION.match(node.node_key)
    key_operation = match.group(1) if match else None
    operation = update.get("operation")
    if operation not in _OPERATIONS:
        raise structure_error(
            graph,
            node=node,
            reason="invalid_regimen_operation",
            operation=operation,
        )
    if key_operation != operation:
        raise structure_error(
            graph,
            node=node,
            reason="regimen_operation_does_not_match_node_key",
            operation=operation,
            key_operation=key_operation,
        )
    components = update.get("components", [])
    alternatives = update.get("alternatives", [])
    if not isinstance(components, (list, tuple)) or not isinstance(alternatives, (list, tuple)):
        raise structure_error(
            graph,
            node=node,
            reason="regimen_components_and_alternatives_must_be_arrays",
        )
    if operation == "MAINTAIN" and (components or alternatives):
        raise structure_error(
            graph,
            node=node,
            reason="maintain_regimen_must_not_contain_components",
        )
    if operation != "MAINTAIN" and not components and not alternatives:
        raise structure_error(
            graph,
            node=node,
            reason="regimen_update_requires_components_or_alternatives",
        )
