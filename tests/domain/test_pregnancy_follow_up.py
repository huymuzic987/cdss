from cdss.domain.decision_tree import ExecutedAction, NodeType
from cdss.domain.pregnancy_follow_up import (
    MINIMUM_PREGNANCY_FOLLOW_UPS,
    PregnancyFollowUpPhase,
    summarize_pregnancy_follow_up,
)


def _action(*, follow_up_required: bool) -> ExecutedAction:
    return ExecutedAction(
        tree_key="hypertension-in-pregnancy",
        node_key="T12_END",
        node_type=NodeType.END,
        text_en="Result",
        text_vi="Kết quả",
        payload={"follow_up_required": follow_up_required},
    )


def test_four_encounters_complete_the_minimum_three_pregnancy_follow_ups() -> None:
    summary = summarize_pregnancy_follow_up(
        {
            "is_pregnant": True,
            "pregnancy_episode_id": "pregnancy-demo-001",
            "pregnancy_follow_up_number": 3,
        },
        patient_id="patient-001",
        encounter_ids=("initial", "follow-up-1", "follow-up-2", "follow-up-3"),
        actions=[_action(follow_up_required=True)],
    )

    assert summary is not None
    assert summary.episode_id == "pregnancy-demo-001"
    assert summary.encounter_count == 4
    assert summary.follow_up_number == 3
    assert summary.phase == PregnancyFollowUpPhase.FOLLOW_UP_3
    assert summary.minimum_follow_ups_required == MINIMUM_PREGNANCY_FOLLOW_UPS
    assert summary.minimum_follow_ups_completed is True
    assert summary.next_follow_up_number == 4
    assert summary.next_follow_up_required is True


def test_emergency_terminal_does_not_schedule_another_follow_up() -> None:
    summary = summarize_pregnancy_follow_up(
        {"is_pregnant": True},
        patient_id="patient-002",
        encounter_ids=("initial",),
        actions=[_action(follow_up_required=False)],
    )

    assert summary is not None
    assert summary.phase == PregnancyFollowUpPhase.INITIAL
    assert summary.next_follow_up_number is None
    assert summary.next_follow_up_required is False


def test_non_pregnancy_evaluation_has_no_pregnancy_episode() -> None:
    assert (
        summarize_pregnancy_follow_up(
            {"is_pregnant": False, "is_postpartum": False},
            patient_id="patient-003",
            encounter_ids=(),
            actions=[],
        )
        is None
    )
