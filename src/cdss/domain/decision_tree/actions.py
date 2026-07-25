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
from cdss.domain.decision_tree.medicine_catalog import MedicineRepository


def collect_action(
    node: NodeDefinition,
    run_state: RunState,
    *,
    tree_key: str,
    medicine_repository: MedicineRepository | None = None,
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

    if node.node_type is NodeType.END and medicine_repository is not None:
        action_type = payload.get("action_type")
        if action_type in START_COMBINATION_ACTION_TYPES:
            medicine_options = build_medicine_options(run_state.context, medicine_repository)
            if medicine_options is not None:
                payload["medicine_options"] = cast(JsonValue, medicine_options)
        if isinstance(action_type, str):
            medicines = resolve_single_drug_medicines(action_type, medicine_repository)
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


def select_output_actions(
    actions: list[ExecutedAction], *, debug_output: bool
) -> list[ExecutedAction]:
    """Collapse a run's action trail down to its single terminal action.

    A tree can walk through several ACTION nodes that exist only to record
    an intermediate step of that tree's own logic (e.g. drug-combination's
    duplicate-drug-class and prior-regimen checks) before reaching the node
    that actually ends the walk -- every one of them gets appended to
    ``actions`` for audit purposes, but only the last entry is the tree's
    real recommendation. Non-debug callers get just that; debug_output
    callers get the full trail unchanged.
    """
    if debug_output or len(actions) <= 1:
        return actions
    return [actions[-1]]
