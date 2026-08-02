from datetime import date
from types import SimpleNamespace
from typing import Any, cast

from cdss.domain.decision_tree import ExecutedAction, NodeType, TraversalResult
from cdss.domain.follow_up import (
    FollowUpType,
    MedicationFollowUpAssessment,
    MedicationFollowUpOutcome,
    build_current_visit_input,
    build_previous_visit_input,
    evaluate_medication_follow_up,
    infer_follow_up,
    is_bp_target_reached,
)


def _action(*, tree_key: str = "test-tree", **payload: Any) -> ExecutedAction:
    return ExecutedAction(
        tree_key=tree_key,
        node_key="test-action",
        node_type=NodeType.ACTION,
        text_en="test",
        text_vi="test",
        payload=payload,
    )


def _result(actions: list[ExecutedAction], context: dict[str, Any]) -> TraversalResult:
    return cast(TraversalResult, SimpleNamespace(actions=actions, context=context))


def test_previous_visit_input_replays_previous_bp_as_initial_visit() -> None:
    result = build_previous_visit_input(
        {
            "previous_sbp": 150,
            "previous_dbp": 95,
            "current_clinic_sbp": 125,
            "current_clinic_dbp": 75,
            "has_type_2_diabetes": True,
            "is_medication_follow_up": True,
            "medication_follow_up_stage": "ESCALATED_REGIMEN",
        }
    )

    assert result["current_clinic_sbp"] == 150
    assert result["current_clinic_dbp"] == 95
    assert result["has_type_2_diabetes"] is True
    assert result["is_medication_follow_up"] is False
    assert "medication_follow_up_stage" not in result


def test_medication_recommendation_takes_precedence_and_restores_state() -> None:
    target = {
        "sbp": {"upper_exclusive_mmhg": 130},
        "dbp": {"upper_exclusive_mmhg": 80},
    }
    inference = infer_follow_up(
        _result(
            [
                _action(
                    action_type="LIFESTYLE_AND_CONTINUED_MONITORING",
                    follow_up_required=True,
                ),
                _action(
                    action_type="INITIAL_TWO_DRUG_COMBINATION",
                    follow_up_required=True,
                    next_medication_follow_up_stage="INITIAL_REGIMEN",
                ),
            ],
            {"treatment": {"bp_target": target}},
        )
    )

    assert inference.follow_up_type == FollowUpType.MEDICATION_FOLLOW_UP
    current = build_current_visit_input({"previous_sbp": 150, "previous_dbp": 95}, inference)
    assert current["is_medication_follow_up"] is True
    assert current["is_lifestyle_follow_up"] is False
    assert current["active_bp_target"] == target
    assert current["medication_follow_up_stage"] == "INITIAL_REGIMEN"


def test_lifestyle_recommendation_builds_lifestyle_follow_up_input() -> None:
    inference = infer_follow_up(
        _result(
            [
                _action(
                    action_type="LIFESTYLE_AND_CONTINUED_MONITORING",
                    follow_up_required=True,
                )
            ],
            {},
        )
    )

    assert inference.follow_up_type == FollowUpType.LIFESTYLE_FOLLOW_UP
    current = build_current_visit_input({"previous_sbp": 130, "previous_dbp": 85}, inference)
    assert current["is_lifestyle_follow_up"] is True
    assert current["is_medication_follow_up"] is False
    assert current["pre_lifestyle_clinic_sbp"] == 130
    assert current["pre_lifestyle_clinic_dbp"] == 85


def test_pregnancy_recommendation_keeps_follow_up_on_initial_tree() -> None:
    inference = infer_follow_up(
        _result(
            [
                _action(
                    tree_key="hypertension-in-pregnancy",
                    action_type="MAINTAIN_CURRENT_REGIMEN",
                    follow_up_required=True,
                )
            ],
            {},
        )
    )

    assert inference.follow_up_type == FollowUpType.PREGNANCY_FOLLOW_UP
    current = build_current_visit_input({"previous_sbp": 140, "previous_dbp": 85}, inference)
    assert current["is_pregnancy_follow_up"] is True
    assert current["is_lifestyle_follow_up"] is False
    assert current["is_medication_follow_up"] is False


def _medication_assessment(**overrides: Any) -> MedicationFollowUpAssessment:
    values: dict[str, Any] = {
        "clinic_sbp": 135,
        "clinic_dbp": 85,
        "active_bp_target": {
            "sbp": {"upper_exclusive_mmhg": 130},
            "dbp": {"upper_exclusive_mmhg": 80},
        },
        "assessment_date": date(2026, 6, 29),
        "regimen_effective_date": date(2026, 6, 1),
        "minimum_regimen_days": 28,
        "current_regimen_drug_classes": ("A", "D"),
    }
    values.update(overrides)
    return MedicationFollowUpAssessment(**values)


def test_target_requires_both_readings_below_exclusive_limits() -> None:
    target = _medication_assessment().active_bp_target

    assert is_bp_target_reached(129, 79, target) is True
    assert is_bp_target_reached(130, 79, target) is False
    assert is_bp_target_reached(129, 80, target) is False


def test_controlled_bp_continues_traversal_to_maintenance_action() -> None:
    decision = evaluate_medication_follow_up(_medication_assessment(clinic_sbp=125, clinic_dbp=75))

    assert decision.outcome == MedicationFollowUpOutcome.MAINTAIN_CONTROLLED
    assert decision.should_continue_traversal is True
    assert decision.duration_sufficient is None


def test_drug_replacement_stays_at_stage_and_resets_regimen_clock() -> None:
    decision = evaluate_medication_follow_up(
        _medication_assessment(
            assessment_date=date(2026, 6, 15),
            drug_replacement_required=True,
        )
    )

    assert decision.outcome == MedicationFollowUpOutcome.REPLACE_DRUG_SAME_STAGE
    assert decision.current_regimen_drug_classes == ("A", "D")
    assert decision.should_continue_traversal is False
    assert decision.regimen_effective_date == date(2026, 6, 15)
    assert decision.next_follow_up_date == date(2026, 7, 13)


def test_early_unchanged_regimen_continues_until_original_reassessment() -> None:
    decision = evaluate_medication_follow_up(
        _medication_assessment(assessment_date=date(2026, 6, 15))
    )

    assert decision.outcome == MedicationFollowUpOutcome.CONTINUE_UNTIL_REASSESSMENT
    assert decision.should_continue_traversal is False
    assert decision.duration_sufficient is False
    assert decision.next_follow_up_date == date(2026, 6, 29)


def test_inadequate_adherence_or_dose_stops_escalation() -> None:
    decision = evaluate_medication_follow_up(_medication_assessment(adherence_adequate=False))

    assert decision.outcome == MedicationFollowUpOutcome.ADDRESS_ADHERENCE_OR_DOSE
    assert decision.should_continue_traversal is False
    assert decision.duration_sufficient is True


def test_evaluable_uncontrolled_regimen_continues_to_escalation() -> None:
    decision = evaluate_medication_follow_up(_medication_assessment())

    assert decision.outcome == MedicationFollowUpOutcome.ESCALATE_REGIMEN
    assert decision.should_continue_traversal is True
    assert decision.duration_sufficient is True
