"""Infer the current encounter workflow from a previous guideline run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cdss.domain.decision_tree import ExecutedAction, JsonObject, TraversalResult


class FollowUpType(StrEnum):
    INITIAL_VISIT = "INITIAL_VISIT"
    LIFESTYLE_FOLLOW_UP = "LIFESTYLE_FOLLOW_UP"
    MEDICATION_FOLLOW_UP = "MEDICATION_FOLLOW_UP"
    PREGNANCY_FOLLOW_UP = "PREGNANCY_FOLLOW_UP"


@dataclass(frozen=True)
class FollowUpInference:
    follow_up_type: FollowUpType
    previous_action_types: tuple[str, ...] = ()
    active_bp_target: JsonObject | None = None
    medication_follow_up_stage: str | None = None


def has_complete_previous_bp(runtime_input: Mapping[str, Any]) -> bool:
    return (
        runtime_input.get("previous_sbp") is not None
        and runtime_input.get("previous_dbp") is not None
    )


def build_previous_visit_input(runtime_input: Mapping[str, Any]) -> JsonObject:
    """Replay the previous BP as a non-follow-up encounter."""
    previous_sbp = runtime_input.get("previous_sbp")
    previous_dbp = runtime_input.get("previous_dbp")
    if previous_sbp is None or previous_dbp is None:
        raise ValueError("Both previous_sbp and previous_dbp are required")

    previous: JsonObject = dict(runtime_input)
    previous.update(
        {
            "current_clinic_sbp": previous_sbp,
            "current_clinic_dbp": previous_dbp,
            "is_lifestyle_follow_up": False,
            "is_medication_follow_up": False,
        }
    )
    previous.pop("active_bp_target", None)
    previous.pop("medication_follow_up_stage", None)
    return previous


def infer_follow_up(previous_result: TraversalResult) -> FollowUpInference:
    """Classify the next visit from the previous guideline recommendations."""
    action_types = tuple(
        action_type
        for action in previous_result.actions
        if isinstance((action_type := action.payload.get("action_type")), str)
    )
    medication_stage = _last_string_payload(
        previous_result.actions, "next_medication_follow_up_stage"
    )
    bp_target = _bp_target(previous_result.context)

    if medication_stage is not None:
        return FollowUpInference(
            FollowUpType.MEDICATION_FOLLOW_UP,
            action_types,
            bp_target,
            medication_stage,
        )
    if any(_is_lifestyle_follow_up_action(action) for action in previous_result.actions):
        return FollowUpInference(
            FollowUpType.LIFESTYLE_FOLLOW_UP,
            action_types,
            bp_target,
        )
    if any(_is_pregnancy_follow_up_action(action) for action in previous_result.actions):
        return FollowUpInference(
            FollowUpType.PREGNANCY_FOLLOW_UP,
            action_types,
            bp_target,
        )
    return FollowUpInference(FollowUpType.INITIAL_VISIT, action_types, bp_target)


def build_current_visit_input(
    runtime_input: Mapping[str, Any], inference: FollowUpInference
) -> JsonObject:
    """Inject inferred workflow state for today's traversal."""
    current: JsonObject = dict(runtime_input)
    current["is_lifestyle_follow_up"] = inference.follow_up_type == FollowUpType.LIFESTYLE_FOLLOW_UP
    current["is_medication_follow_up"] = (
        inference.follow_up_type == FollowUpType.MEDICATION_FOLLOW_UP
    )
    current["is_pregnancy_follow_up"] = inference.follow_up_type == FollowUpType.PREGNANCY_FOLLOW_UP

    if inference.follow_up_type == FollowUpType.LIFESTYLE_FOLLOW_UP:
        current["pre_lifestyle_clinic_sbp"] = current["previous_sbp"]
        current["pre_lifestyle_clinic_dbp"] = current["previous_dbp"]
    elif inference.follow_up_type == FollowUpType.MEDICATION_FOLLOW_UP:
        if inference.active_bp_target is not None:
            current["active_bp_target"] = inference.active_bp_target
        if inference.medication_follow_up_stage is not None:
            current["medication_follow_up_stage"] = inference.medication_follow_up_stage
    return current


def _last_string_payload(actions: list[ExecutedAction], key: str) -> str | None:
    for action in reversed(actions):
        value = action.payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _is_lifestyle_follow_up_action(action: ExecutedAction) -> bool:
    action_type = action.payload.get("action_type")
    return (
        action.payload.get("follow_up_required") is True
        and isinstance(action_type, str)
        and "LIFESTYLE" in action_type
    )


def _is_pregnancy_follow_up_action(action: ExecutedAction) -> bool:
    return (
        action.tree_key == "hypertension-in-pregnancy"
        and action.payload.get("follow_up_required") is True
    )


def _bp_target(context: Mapping[str, Any]) -> JsonObject | None:
    treatment = context.get("treatment")
    if not isinstance(treatment, dict):
        return None
    target = treatment.get("bp_target")
    return dict(target) if isinstance(target, dict) else None
