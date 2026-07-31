from types import SimpleNamespace
from typing import Any, cast

from cdss.domain.decision_tree import ExecutedAction, NodeType, TraversalResult
from cdss.domain.follow_up import (
    FollowUpType,
    build_current_visit_input,
    build_previous_visit_input,
    infer_follow_up,
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
