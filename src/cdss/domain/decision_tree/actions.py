"""Action collection for entered decision-tree nodes."""

from __future__ import annotations

from typing import cast

from cdss.domain.decision_tree.contracts import (
    ExecutedAction,
    JsonValue,
    NodeType,
    RunState,
    copy_json_value,
)
from cdss.domain.decision_tree.drug_classes import (
    START_COMBINATION_ACTION_TYPES,
    build_medicine_options,
    resolve_single_drug_medicines,
)
from cdss.domain.decision_tree.errors import InvalidTreeStructure
from cdss.domain.decision_tree.graph import NodeDefinition


def collect_action(
    node: NodeDefinition,
    run_state: RunState,
    *,
    tree_key: str,
) -> ExecutedAction | None:
    """Append a detached action payload for an ACTION or END node."""

    if node.action_payload is None:
        return None
    if node.node_type not in {NodeType.ACTION, NodeType.END}:
        raise InvalidTreeStructure(
            tree_key=tree_key,
            node_key=node.node_key,
            details={"reason": "action_payload_on_unsupported_node_type"},
            partial_run_state=run_state,
        )

    try:
        payload = copy_json_value(node.action_payload)
    except TypeError as exc:
        raise InvalidTreeStructure(
            tree_key=tree_key,
            node_key=node.node_key,
            details={"reason": "action_payload_is_not_json_object"},
            partial_run_state=run_state,
        ) from exc
    if not isinstance(payload, dict):
        raise InvalidTreeStructure(
            tree_key=tree_key,
            node_key=node.node_key,
            details={"reason": "action_payload_is_not_json_object"},
            partial_run_state=run_state,
        )

    if node.node_type is NodeType.END:
        action_type = payload.get("action_type")
        if action_type in START_COMBINATION_ACTION_TYPES:
            medicine_options = build_medicine_options(run_state.context)
            if medicine_options is not None:
                payload["medicine_options"] = cast(JsonValue, medicine_options)
        if isinstance(action_type, str):
            medicines = resolve_single_drug_medicines(action_type)
            if medicines is not None:
                payload["medicines"] = cast(JsonValue, medicines)

    action = ExecutedAction(
        tree_key=tree_key,
        node_key=node.node_key,
        node_type=node.node_type,
        text_en=node.text_en,
        text_vi=node.text_vi,
        payload=payload,
    )
    run_state.actions.append(action)
    return action
