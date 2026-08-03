"""Stateless medication follow-up assessment decisions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Any


class MedicationFollowUpOutcome(StrEnum):
    MAINTAIN_CONTROLLED = "MAINTAIN_CONTROLLED"
    CONTINUE_UNTIL_REASSESSMENT = "CONTINUE_UNTIL_REASSESSMENT"
    REPLACE_DRUG_SAME_STAGE = "REPLACE_DRUG_SAME_STAGE"
    ADDRESS_ADHERENCE_OR_DOSE = "ADDRESS_ADHERENCE_OR_DOSE"
    ESCALATE_REGIMEN = "ESCALATE_REGIMEN"


@dataclass(frozen=True)
class MedicationFollowUpAssessment:
    clinic_sbp: float
    clinic_dbp: float
    active_bp_target: Mapping[str, Any]
    assessment_date: date
    regimen_effective_date: date
    minimum_regimen_days: int
    current_regimen_drug_classes: tuple[str, ...] = ()
    drug_replacement_required: bool = False
    adherence_adequate: bool = True
    dose_adequate: bool = True


@dataclass(frozen=True)
class MedicationFollowUpDecision:
    outcome: MedicationFollowUpOutcome
    should_continue_traversal: bool
    bp_target_reached: bool
    duration_sufficient: bool | None
    regimen_effective_date: date
    next_follow_up_date: date | None
    current_regimen_drug_classes: tuple[str, ...]


def is_bp_target_reached(
    clinic_sbp: float,
    clinic_dbp: float,
    active_bp_target: Mapping[str, Any],
) -> bool:
    """Return whether both clinic readings are below their active upper limits."""
    sbp_limit = _target_upper_limit(active_bp_target, "sbp")
    dbp_limit = _target_upper_limit(active_bp_target, "dbp")
    return clinic_sbp < sbp_limit and clinic_dbp < dbp_limit


def needs_same_stage_drug_replacement(assessment: MedicationFollowUpAssessment) -> bool:
    """Check whether an individual drug must change without escalating the regimen."""
    return assessment.drug_replacement_required


def regimen_duration_is_sufficient(assessment: MedicationFollowUpAssessment) -> bool:
    """Check time on the unchanged regimen, including its effective date."""
    if assessment.minimum_regimen_days < 0:
        raise ValueError("minimum_regimen_days cannot be negative")
    if assessment.regimen_effective_date > assessment.assessment_date:
        raise ValueError("regimen_effective_date cannot be after assessment_date")
    elapsed_days = (assessment.assessment_date - assessment.regimen_effective_date).days
    return elapsed_days >= assessment.minimum_regimen_days


def regimen_is_ready_for_escalation(assessment: MedicationFollowUpAssessment) -> bool:
    """Require adequate adherence and dose before advancing treatment."""
    return assessment.adherence_adequate and assessment.dose_adequate


def next_regimen_follow_up_date(effective_date: date, minimum_regimen_days: int) -> date:
    """Calculate the first date on which the regimen can be reassessed."""
    if minimum_regimen_days < 0:
        raise ValueError("minimum_regimen_days cannot be negative")
    return effective_date + timedelta(days=minimum_regimen_days)


def evaluate_medication_follow_up(
    assessment: MedicationFollowUpAssessment,
) -> MedicationFollowUpDecision:
    """Run the stateless follow-up gates and decide whether traversal may continue."""
    target_reached = is_bp_target_reached(
        assessment.clinic_sbp,
        assessment.clinic_dbp,
        assessment.active_bp_target,
    )
    if target_reached:
        return _medication_decision(
            assessment, MedicationFollowUpOutcome.MAINTAIN_CONTROLLED, True, None, None
        )

    if needs_same_stage_drug_replacement(assessment):
        new_effective_date = assessment.assessment_date
        return MedicationFollowUpDecision(
            outcome=MedicationFollowUpOutcome.REPLACE_DRUG_SAME_STAGE,
            should_continue_traversal=False,
            bp_target_reached=False,
            duration_sufficient=None,
            regimen_effective_date=new_effective_date,
            next_follow_up_date=next_regimen_follow_up_date(
                new_effective_date, assessment.minimum_regimen_days
            ),
            current_regimen_drug_classes=assessment.current_regimen_drug_classes,
        )

    duration_sufficient = regimen_duration_is_sufficient(assessment)
    if not duration_sufficient:
        return _medication_decision(
            assessment,
            MedicationFollowUpOutcome.CONTINUE_UNTIL_REASSESSMENT,
            False,
            False,
            next_regimen_follow_up_date(
                assessment.regimen_effective_date, assessment.minimum_regimen_days
            ),
        )

    if not regimen_is_ready_for_escalation(assessment):
        return _medication_decision(
            assessment,
            MedicationFollowUpOutcome.ADDRESS_ADHERENCE_OR_DOSE,
            False,
            True,
            None,
        )

    return _medication_decision(
        assessment, MedicationFollowUpOutcome.ESCALATE_REGIMEN, True, True, None
    )


def _medication_decision(
    assessment: MedicationFollowUpAssessment,
    outcome: MedicationFollowUpOutcome,
    should_continue: bool,
    duration_sufficient: bool | None,
    next_follow_up_date: date | None,
) -> MedicationFollowUpDecision:
    return MedicationFollowUpDecision(
        outcome=outcome,
        should_continue_traversal=should_continue,
        bp_target_reached=outcome == MedicationFollowUpOutcome.MAINTAIN_CONTROLLED,
        duration_sufficient=duration_sufficient,
        regimen_effective_date=assessment.regimen_effective_date,
        next_follow_up_date=next_follow_up_date,
        current_regimen_drug_classes=assessment.current_regimen_drug_classes,
    )


def _target_upper_limit(active_bp_target: Mapping[str, Any], axis: str) -> float:
    target = active_bp_target.get(axis)
    value = target.get("upper_exclusive_mmhg") if isinstance(target, Mapping) else None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"active_bp_target.{axis}.upper_exclusive_mmhg is required")
    return float(value)
