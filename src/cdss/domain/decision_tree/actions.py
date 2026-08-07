"""Action collection for entered decision-tree nodes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from cdss.domain.decision_tree.contracts import (
    ExecutedAction,
    JsonObject,
    JsonValue,
    NodeType,
    RunState,
    copy_json_value,
)
from cdss.domain.decision_tree.drug_classes import (
    START_COMBINATION_ACTION_TYPES,
    resolve_single_drug_medicines,
)
from cdss.domain.decision_tree.errors import InvalidTreeStructure
from cdss.domain.decision_tree.graph import NodeDefinition
from cdss.domain.decision_tree.medicine_catalog import MedicineRepository
from cdss.domain.medication_safety.medication_safety import (
    evaluate_medication_safety,
    evaluate_target,
)
from cdss.domain.medication_safety.medication_safety_action_catalog import (
    ACTION_SELECTOR_ACTION_TYPES,
    ACTION_SELECTORS,
)
from cdss.domain.medication_safety.medication_safety_metadata import candidate_regimens
from cdss.domain.medication_safety.medication_safety_resolver import resolve_safe_regimens


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

    if medicine_repository is not None:
        action_type = payload.get("action_type")
        if (
            action_type in START_COMBINATION_ACTION_TYPES
            or action_type in ACTION_SELECTOR_ACTION_TYPES
            or payload.get("candidate_regimens")
            or payload.get("medicine_options")
        ):
            supplied_options = payload.get("medicine_options")
            supplied_regimens: list[list[str]] = []
            if isinstance(supplied_options, list):
                for option in supplied_options:
                    if not isinstance(option, Mapping):
                        continue
                    classes = option.get("classes")
                    if isinstance(classes, list):
                        supplied_regimens.append(
                            [item for item in classes if isinstance(item, str)]
                        )
            options, safety, had_candidates = resolve_safe_regimens(
                payload, run_state.context, run_state.input_snapshot, medicine_repository
            )
            if had_candidates:
                payload["medicine_options"] = cast(JsonValue, options)
                payload["medication_safety"] = cast(JsonValue, safety)
                payload["requires_safety_evaluation"] = True
                payload["clinical_context"] = payload.get(
                    "clinical_context",
                    "acute_emergency" if payload.get("target_timing") else "chronic_hypertension",
                )
                candidates = supplied_regimens or candidate_regimens(
                    payload, run_state.context, options
                )
                if not candidates and isinstance(action_type, str):
                    candidates = ACTION_SELECTORS.get(action_type, [])
                payload["candidate_regimens"] = cast(JsonValue, candidates)
                _mark_no_safe_option(payload, action_type, options)
        if node.node_type is NodeType.END and isinstance(action_type, str):
            medicines = resolve_single_drug_medicines(action_type, medicine_repository)
            if medicines is not None:
                safe_medicines, safety = _filter_single_medicines(
                    medicines, run_state.input_snapshot, payload
                )
                payload["medicines"] = cast(JsonValue, safe_medicines)
                payload["medication_safety"] = cast(JsonValue, safety)
                payload["requires_safety_evaluation"] = True
                payload["clinical_context"] = payload.get(
                    "clinical_context",
                    "acute_emergency" if payload.get("target_timing") else "chronic_hypertension",
                )

    if medicine_repository is not None:
        active = run_state.input_snapshot.get("active_medication_regimen")
        if isinstance(active, (list, tuple)) and active:
            current_safety = evaluate_medication_safety(run_state.input_snapshot, medicines=active)
            payload["current_regimen_safety"] = cast(JsonValue, current_safety)
            if current_safety.get("findings"):
                payload["current_regimen_review_required"] = True

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


def _mark_no_safe_option(
    payload: JsonObject, action_type: object, options: list[JsonObject]
) -> None:
    if options or not isinstance(action_type, str):
        return
    payload["original_action_type"] = action_type
    payload["action_type"] = "NO_SAFE_OPTION"
    payload["recommendation_status"] = "NO_SAFE_OPTION"


def _filter_single_medicines(
    medicines: list[JsonObject], runtime: object, payload: Mapping[str, object]
) -> tuple[list[JsonObject], JsonObject]:
    runtime_mapping = runtime if isinstance(runtime, Mapping) else {}
    context = "acute_emergency" if payload.get("target_timing") else "chronic_hypertension"
    safe: list[JsonObject] = []
    findings: list[JsonObject] = []
    requires_override_reason = False
    for medicine in medicines:
        result = evaluate_target(
            str(medicine.get("drug_class") or "OTHER"),
            runtime_mapping,
            medicine=medicine,
            clinical_context=context,
        )
        findings.extend(result["findings"])
        if result["status"] not in {"ABSOLUTE", "INSUFFICIENT_DATA"}:
            item = {
                **medicine,
                "safety_status": result["status"],
                "safety_findings": result["findings"],
            }
            if result["status"] == "RELATIVE":
                item["requires_override_reason"] = True
                requires_override_reason = True
            safe.append(item)
    profile = evaluate_medication_safety(runtime_mapping)
    profile["findings"] = findings
    profile["blocked_targets"] = sorted(
        {str(item["target"]) for item in findings if item["severity"] == "ABSOLUTE"}
    )
    profile["review_targets"] = sorted(
        {
            str(item["target"])
            for item in findings
            if item["severity"] in {"INSUFFICIENT_DATA", "RELATIVE"}
        }
    )
    profile["requires_override_reason"] = requires_override_reason
    return safe, profile


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
