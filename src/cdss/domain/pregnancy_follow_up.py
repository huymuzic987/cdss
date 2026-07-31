"""Longitudinal metadata for the stateless pregnancy-hypertension pathway."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cdss.domain.decision_tree import ExecutedAction

MINIMUM_PREGNANCY_FOLLOW_UPS = 3


class PregnancyFollowUpPhase(StrEnum):
    INITIAL = "INITIAL"
    FOLLOW_UP_1 = "FOLLOW_UP_1"
    FOLLOW_UP_2 = "FOLLOW_UP_2"
    FOLLOW_UP_3 = "FOLLOW_UP_3"
    CONTINUING = "CONTINUING"


@dataclass(frozen=True)
class PregnancyFollowUpSummary:
    episode_id: str
    encounter_count: int
    follow_up_number: int
    phase: PregnancyFollowUpPhase
    minimum_follow_ups_required: int
    minimum_follow_ups_completed: bool
    next_follow_up_number: int | None
    next_follow_up_required: bool


def summarize_pregnancy_follow_up(
    runtime_input: Mapping[str, Any],
    *,
    patient_id: str,
    encounter_ids: Sequence[str],
    actions: Sequence[ExecutedAction],
) -> PregnancyFollowUpSummary | None:
    """Describe the pregnancy episode carried by a canonical longitudinal Bundle."""

    if not (runtime_input.get("is_pregnant") is True or runtime_input.get("is_postpartum") is True):
        return None

    encounter_count = max(1, len(encounter_ids))
    derived_follow_up_number = encounter_count - 1
    declared_follow_up_number = runtime_input.get("pregnancy_follow_up_number")
    if isinstance(declared_follow_up_number, int) and not isinstance(
        declared_follow_up_number, bool
    ):
        follow_up_number = declared_follow_up_number
    else:
        follow_up_number = derived_follow_up_number

    episode_id = runtime_input.get("pregnancy_episode_id")
    if not isinstance(episode_id, str) or not episode_id.strip():
        episode_id = f"pregnancy-{patient_id}"

    next_required = any(
        action.tree_key == "hypertension-in-pregnancy"
        and action.payload.get("follow_up_required") is True
        for action in actions
    )
    return PregnancyFollowUpSummary(
        episode_id=episode_id,
        encounter_count=encounter_count,
        follow_up_number=follow_up_number,
        phase=_phase(follow_up_number),
        minimum_follow_ups_required=MINIMUM_PREGNANCY_FOLLOW_UPS,
        minimum_follow_ups_completed=follow_up_number >= MINIMUM_PREGNANCY_FOLLOW_UPS,
        next_follow_up_number=follow_up_number + 1 if next_required else None,
        next_follow_up_required=next_required,
    )


def _phase(follow_up_number: int) -> PregnancyFollowUpPhase:
    if follow_up_number <= 0:
        return PregnancyFollowUpPhase.INITIAL
    if follow_up_number == 1:
        return PregnancyFollowUpPhase.FOLLOW_UP_1
    if follow_up_number == 2:
        return PregnancyFollowUpPhase.FOLLOW_UP_2
    if follow_up_number == 3:
        return PregnancyFollowUpPhase.FOLLOW_UP_3
    return PregnancyFollowUpPhase.CONTINUING
