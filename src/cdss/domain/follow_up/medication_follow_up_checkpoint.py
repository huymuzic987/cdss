"""Apply medication follow-up decisions at decision-tree BP checkpoints."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from cdss.domain.decision_tree.contracts import ExecutedAction, NodeType, RunState
from cdss.domain.decision_tree.graph import NodeDefinition
from cdss.domain.follow_up.medication_follow_up import (
    MedicationFollowUpAssessment,
    MedicationFollowUpDecision,
    MedicationFollowUpOutcome,
    evaluate_medication_follow_up,
    next_regimen_follow_up_date,
)

_BP_CHECKPOINT_MARKER = "_BP_TARGET_"
_RESISTANT_ADD_DRUG_COUNTS = {
    "T13_A_ADD_MRA": 4,
    "T13_A_ADD_SPIRONOLACTONE": 4,
}


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

    assessment = MedicationFollowUpAssessment(
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
    resistant_regimen_started = _resistant_action_adds_drug(current, input_data)
    decision = (
        _new_resistant_regimen_decision(assessment)
        if resistant_regimen_started
        else evaluate_medication_follow_up(assessment)
    )
    summary = _decision_summary(decision, current.node_key)
    run_state.context["medication_follow_up"] = summary

    if decision.should_continue_traversal:
        return True

    # The resistant-HTN action that was just entered is the new prescription
    # and must remain the presented clinical recommendation. The follow-up
    # context still supplies its newly calculated reassessment date, but a
    # synthetic "continue regimen" action would hide ADD_MRA/ADD_SPIRONOLACTONE
    # because non-debug responses select the last collected action.
    if resistant_regimen_started:
        return False

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


def _decision_summary(
    decision: MedicationFollowUpDecision,
    checkpoint_node_key: str,
) -> dict[str, Any]:
    return {
        "outcome": decision.outcome.value,
        "should_continue_traversal": decision.should_continue_traversal,
        "bp_target_reached": decision.bp_target_reached,
        "duration_sufficient": decision.duration_sufficient,
        "regimen_effective_date": decision.regimen_effective_date.isoformat(),
        "next_follow_up_date": (
            decision.next_follow_up_date.isoformat() if decision.next_follow_up_date else None
        ),
        "checkpoint_node_key": checkpoint_node_key,
        "current_regimen_drug_classes": list(decision.current_regimen_drug_classes),
        "current_regimen_label": "+".join(decision.current_regimen_drug_classes),
    }


def _resistant_action_adds_drug(
    current: NodeDefinition,
    input_data: Mapping[str, Any],
) -> bool:
    """Return whether this resistant-HTN action prescribes a drug not yet taken.

    The BP conditions after these actions describe a later reassessment, not the
    current encounter. The compact FHIR contract represents MRA/spironolactone
    through the regimen count because they are outside the A/B/C/D class codes.
    """
    expected_count = _RESISTANT_ADD_DRUG_COUNTS.get(current.node_key)
    if expected_count is None:
        return False
    current_count = input_data.get("current_regimen_drug_count")
    if not isinstance(current_count, int) or isinstance(current_count, bool):
        return False
    return current_count < expected_count


def _new_resistant_regimen_decision(
    assessment: MedicationFollowUpAssessment,
) -> MedicationFollowUpDecision:
    effective_date = assessment.assessment_date
    return MedicationFollowUpDecision(
        outcome=MedicationFollowUpOutcome.CONTINUE_UNTIL_REASSESSMENT,
        should_continue_traversal=False,
        bp_target_reached=False,
        duration_sufficient=False,
        regimen_effective_date=effective_date,
        next_follow_up_date=next_regimen_follow_up_date(
            effective_date, assessment.minimum_regimen_days
        ),
        current_regimen_drug_classes=assessment.current_regimen_drug_classes,
    )


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
