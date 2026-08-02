"""Stateless medication follow-up decisions and public follow-up API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from cdss.domain.decision_tree.contracts import ExecutedAction, NodeType, RunState
from cdss.domain.decision_tree.graph import NodeDefinition
from cdss.domain.follow_up_inference import (
    FollowUpInference,
    FollowUpType,
    build_current_visit_input,
    build_previous_visit_input,
    has_complete_previous_bp,
    infer_follow_up,
)

__all__ = [
    "FollowUpInference",
    "FollowUpType",
    "MedicationFollowUpAssessment",
    "MedicationFollowUpDecision",
    "MedicationFollowUpOutcome",
    "build_current_visit_input",
    "build_previous_visit_input",
    "evaluate_medication_follow_up",
    "evaluate_medication_follow_up_at_bp_checkpoint",
    "has_complete_previous_bp",
    "infer_follow_up",
    "is_bp_target_reached",
    "needs_same_stage_drug_replacement",
    "next_regimen_follow_up_date",
    "regimen_duration_is_sufficient",
    "regimen_is_ready_for_escalation",
]

_BP_CHECKPOINT_MARKER = "_BP_TARGET_"


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


def evaluate_medication_follow_up_at_bp_checkpoint(
    tree_key: str,
    current: NodeDefinition,
    candidates: tuple[NodeDefinition, ...],
    run_state: RunState,
) -> bool:
    """Apply the medication follow-up gate immediately before BP branches.

    The seeded trees already contain their reached/not-reached transitions. This
    hook therefore does not choose a branch. It records the follow-up outcome
    and returns whether the normal candidate evaluation may proceed. It is a
    no-op unless the caller supplied the stateless follow-up scheduling fields.
    """
    if not any(_BP_CHECKPOINT_MARKER in candidate.node_key for candidate in candidates):
        return True

    input_data = run_state.input_snapshot
    if input_data.get("is_medication_follow_up") is not True:
        return True

    required = (
        "assessment_date",
        "regimen_effective_date",
        "minimum_regimen_days",
    )
    if any(input_data.get(name) is None for name in required):
        return True

    treatment = run_state.context.get("treatment")
    active_target = treatment.get("bp_target") if isinstance(treatment, Mapping) else None
    if not isinstance(active_target, Mapping):
        active_target = input_data.get("active_bp_target")
    if not isinstance(active_target, Mapping):
        raise ValueError("active BP target is required at a medication BP checkpoint")

    decision = evaluate_medication_follow_up(
        MedicationFollowUpAssessment(
            clinic_sbp=_required_number(input_data, "current_clinic_sbp"),
            clinic_dbp=_required_number(input_data, "current_clinic_dbp"),
            active_bp_target=active_target,
            assessment_date=_required_date(input_data, "assessment_date"),
            regimen_effective_date=_required_date(input_data, "regimen_effective_date"),
            minimum_regimen_days=_required_integer(input_data, "minimum_regimen_days"),
            current_regimen_drug_classes=_regimen_drug_classes(input_data),
            drug_replacement_required=input_data.get("drug_replacement_required") is True,
            adherence_adequate=input_data.get("adherence_adequate", True) is True,
            dose_adequate=input_data.get("dose_adequate", True) is True,
        )
    )
    summary = {
        "outcome": decision.outcome.value,
        "should_continue_traversal": decision.should_continue_traversal,
        "bp_target_reached": decision.bp_target_reached,
        "duration_sufficient": decision.duration_sufficient,
        "regimen_effective_date": decision.regimen_effective_date.isoformat(),
        "next_follow_up_date": (
            decision.next_follow_up_date.isoformat() if decision.next_follow_up_date else None
        ),
        "checkpoint_node_key": current.node_key,
        "current_regimen_drug_classes": list(decision.current_regimen_drug_classes),
        "current_regimen_label": "+".join(decision.current_regimen_drug_classes),
    }
    run_state.context["medication_follow_up"] = summary

    if decision.should_continue_traversal:
        return True

    run_state.actions.append(
        ExecutedAction(
            tree_key=tree_key,
            node_key=f"{current.node_key}_MEDICATION_FOLLOW_UP_STOP",
            node_type=NodeType.ACTION,
            text_en=_stopped_follow_up_text(decision.outcome),
            text_vi=_stopped_follow_up_text_vi(decision.outcome),
            payload={"action_type": decision.outcome.value, **summary},
        )
    )
    return False


def _required_date(values: Mapping[str, Any], name: str) -> date:
    value = values.get(name)
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO date") from exc
    raise ValueError(f"{name} must be an ISO date")


def _required_number(values: Mapping[str, Any], name: str) -> float:
    value = values.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    return float(value)


def _required_integer(values: Mapping[str, Any], name: str) -> int:
    value = values.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    return value


def _stopped_follow_up_text(outcome: MedicationFollowUpOutcome) -> str:
    return {
        MedicationFollowUpOutcome.CONTINUE_UNTIL_REASSESSMENT: (
            "Continue the current regimen until the scheduled reassessment date"
        ),
        MedicationFollowUpOutcome.REPLACE_DRUG_SAME_STAGE: (
            "Replace the intolerable drug within the same regimen stage and reassess"
        ),
        MedicationFollowUpOutcome.ADDRESS_ADHERENCE_OR_DOSE: (
            "Address adherence or optimize the current dose before escalation"
        ),
    }[outcome]


def _stopped_follow_up_text_vi(outcome: MedicationFollowUpOutcome) -> str:
    return {
        MedicationFollowUpOutcome.CONTINUE_UNTIL_REASSESSMENT: (
            "Tiếp tục phác đồ hiện tại đến ngày tái khám theo lịch"
        ),
        MedicationFollowUpOutcome.REPLACE_DRUG_SAME_STAGE: (
            "Đổi thuốc không dung nạp trong cùng bậc điều trị và hẹn đánh giá lại"
        ),
        MedicationFollowUpOutcome.ADDRESS_ADHERENCE_OR_DOSE: (
            "Xử lý tuân thủ hoặc tối ưu liều hiện tại trước khi tăng bậc điều trị"
        ),
    }[outcome]


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


def _regimen_drug_classes(values: Mapping[str, Any]) -> tuple[str, ...]:
    """Normalize a compact FHIR input value such as ``A+D`` into class codes."""
    value = values.get("current_regimen_drug_classes")
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        classes = tuple(part.strip().upper() for part in value.split("+") if part.strip())
    elif isinstance(value, (list, tuple)):
        classes = tuple(str(part).strip().upper() for part in value if str(part).strip())
    else:
        raise ValueError("current_regimen_drug_classes must be an A+D-style string or list")
    if not classes or any(drug_class not in {"A", "B", "C", "D"} for drug_class in classes):
        raise ValueError("current_regimen_drug_classes may contain only A, B, C, and D")
    if len(classes) != len(set(classes)):
        raise ValueError("current_regimen_drug_classes cannot contain duplicate classes")
    return classes


def _target_upper_limit(active_bp_target: Mapping[str, Any], axis: str) -> float:
    target = active_bp_target.get(axis)
    value = target.get("upper_exclusive_mmhg") if isinstance(target, Mapping) else None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"active_bp_target.{axis}.upper_exclusive_mmhg is required")
    return float(value)
