"""Deterministic read-only patient routes derived from the seeded Trees 1-5."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session

from cdss.domain.decision_tree import (
    LinkTargetNotFound,
    RunState,
    TraceEvent,
    TraversalResult,
    TreeGraph,
    walk_tree,
)
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository

pytestmark = pytest.mark.database

T1 = "hypertension-diagnosis"
T3 = "treatment-threshold-and-bp-target"
T4 = "essential-treatment-strategy"
T5 = "optimal-treatment-strategy"
TREE_KEYS = (T1, "risk-classification", T3, T4, T5)

ACTIVE_BP_TARGET = {
    "dbp": {"upper_exclusive_mmhg": 80},
    "sbp": {
        "lower_reference_mmhg": 120,
        "or_lower": True,
        "upper_exclusive_mmhg": 130,
    },
    "source": "TREE_3_GENERIC",
}

TraceSignature = tuple[str, str, str, str | None, bool | None]
ReferenceSignature = tuple[str, str, int]


def _entered(tree_key: str, node_key: str) -> TraceSignature:
    return (TraceEvent.NODE_ENTERED.value, tree_key, node_key, None, None)


def _candidate(
    tree_key: str,
    node_key: str,
    candidate_node_key: str,
    result: bool,
) -> TraceSignature:
    return (
        TraceEvent.CANDIDATE_EVALUATED.value,
        tree_key,
        node_key,
        candidate_node_key,
        result,
    )


T3_MEDICATION_FULL_RESOURCES = [
    _entered(T3, "T3_START_BP_AND_AGE_INFORMATION"),
    _candidate(T3, "T3_START_BP_AND_AGE_INFORMATION", "T3_C_IS_MEDICATION_FOLLOW_UP", True),
    _entered(T3, "T3_C_IS_MEDICATION_FOLLOW_UP"),
    _candidate(T3, "T3_C_IS_MEDICATION_FOLLOW_UP", "T3_INF_RESTORE_ACTIVE_BP_TARGET", True),
    _entered(T3, "T3_INF_RESTORE_ACTIVE_BP_TARGET"),
    _candidate(
        T3,
        "T3_INF_RESTORE_ACTIVE_BP_TARGET",
        "T3_LINK_ESSENTIAL_TREATMENT_STRATEGY",
        False,
    ),
    _candidate(
        T3,
        "T3_INF_RESTORE_ACTIVE_BP_TARGET",
        "T3_LINK_OPTIMAL_TREATMENT_STRATEGY",
        True,
    ),
    _entered(T3, "T3_LINK_OPTIMAL_TREATMENT_STRATEGY"),
]

T3_MEDICATION_LIMITED_RESOURCES = [
    _entered(T3, "T3_START_BP_AND_AGE_INFORMATION"),
    _candidate(T3, "T3_START_BP_AND_AGE_INFORMATION", "T3_C_IS_MEDICATION_FOLLOW_UP", True),
    _entered(T3, "T3_C_IS_MEDICATION_FOLLOW_UP"),
    _candidate(T3, "T3_C_IS_MEDICATION_FOLLOW_UP", "T3_INF_RESTORE_ACTIVE_BP_TARGET", True),
    _entered(T3, "T3_INF_RESTORE_ACTIVE_BP_TARGET"),
    _candidate(
        T3,
        "T3_INF_RESTORE_ACTIVE_BP_TARGET",
        "T3_LINK_ESSENTIAL_TREATMENT_STRATEGY",
        True,
    ),
    _entered(T3, "T3_LINK_ESSENTIAL_TREATMENT_STRATEGY"),
]

T5_INITIAL_TARGET_REACHED = [
    _entered(T5, "T5_START_BP_AND_AGE_INFORMATION"),
    _candidate(T5, "T5_START_BP_AND_AGE_INFORMATION", "T5_C_IS_MEDICATION_FOLLOW_UP", True),
    _entered(T5, "T5_C_IS_MEDICATION_FOLLOW_UP"),
    _candidate(
        T5,
        "T5_C_IS_MEDICATION_FOLLOW_UP",
        "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        True,
    ),
    _entered(T5, "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN"),
    _candidate(
        T5,
        "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        "T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED",
        True,
    ),
    _entered(T5, "T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED"),
    _candidate(
        T5,
        "T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED",
        "T5_END_INITIAL_REGIMEN_TARGET_REACHED",
        True,
    ),
    _entered(T5, "T5_END_INITIAL_REGIMEN_TARGET_REACHED"),
]

T4_INITIAL_TARGET_REACHED = [
    _entered(T4, "T4_START_BP_AND_AGE_INFORMATION"),
    _candidate(T4, "T4_START_BP_AND_AGE_INFORMATION", "T4_C_IS_MEDICATION_FOLLOW_UP", True),
    _entered(T4, "T4_C_IS_MEDICATION_FOLLOW_UP"),
    _candidate(
        T4,
        "T4_C_IS_MEDICATION_FOLLOW_UP",
        "T4_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        True,
    ),
    _entered(T4, "T4_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN"),
    _candidate(
        T4,
        "T4_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        "T4_C_INITIAL_REGIMEN_BP_TARGET_REACHED",
        True,
    ),
    _entered(T4, "T4_C_INITIAL_REGIMEN_BP_TARGET_REACHED"),
    _candidate(
        T4,
        "T4_C_INITIAL_REGIMEN_BP_TARGET_REACHED",
        "T4_END_MAINTAIN_REGIMEN",
        True,
    ),
    _entered(T4, "T4_END_MAINTAIN_REGIMEN"),
]

T5_INITIAL_TARGET_NOT_REACHED = [
    _entered(T5, "T5_START_BP_AND_AGE_INFORMATION"),
    _candidate(T5, "T5_START_BP_AND_AGE_INFORMATION", "T5_C_IS_MEDICATION_FOLLOW_UP", True),
    _entered(T5, "T5_C_IS_MEDICATION_FOLLOW_UP"),
    _candidate(
        T5,
        "T5_C_IS_MEDICATION_FOLLOW_UP",
        "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        True,
    ),
    _entered(T5, "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN"),
    _candidate(
        T5,
        "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        "T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED",
        False,
    ),
    _candidate(
        T5,
        "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        "T5_C_INITIAL_REGIMEN_BP_TARGET_NOT_REACHED",
        True,
    ),
    _entered(T5, "T5_C_INITIAL_REGIMEN_BP_TARGET_NOT_REACHED"),
    _candidate(
        T5,
        "T5_C_INITIAL_REGIMEN_BP_TARGET_NOT_REACHED",
        "T5_ACTION_FIXED_DOSE_THREE_DRUG_COMBINATION",
        True,
    ),
    _entered(T5, "T5_ACTION_FIXED_DOSE_THREE_DRUG_COMBINATION"),
    _candidate(
        T5,
        "T5_ACTION_FIXED_DOSE_THREE_DRUG_COMBINATION",
        "T5_LINK_THREE_DRUG_TO_TREE_6",
        True,
    ),
    _entered(T5, "T5_LINK_THREE_DRUG_TO_TREE_6"),
]

T5_ESCALATED_TARGET_NOT_REACHED = [
    _entered(T5, "T5_START_BP_AND_AGE_INFORMATION"),
    _candidate(T5, "T5_START_BP_AND_AGE_INFORMATION", "T5_C_IS_MEDICATION_FOLLOW_UP", True),
    _entered(T5, "T5_C_IS_MEDICATION_FOLLOW_UP"),
    _candidate(
        T5,
        "T5_C_IS_MEDICATION_FOLLOW_UP",
        "T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN",
        False,
    ),
    _candidate(
        T5,
        "T5_C_IS_MEDICATION_FOLLOW_UP",
        "T5_C_MEDICATION_FOLLOW_UP_ESCALATED_REGIMEN",
        True,
    ),
    _entered(T5, "T5_C_MEDICATION_FOLLOW_UP_ESCALATED_REGIMEN"),
    _candidate(
        T5,
        "T5_C_MEDICATION_FOLLOW_UP_ESCALATED_REGIMEN",
        "T5_C_ESCALATED_REGIMEN_BP_TARGET_REACHED",
        False,
    ),
    _candidate(
        T5,
        "T5_C_MEDICATION_FOLLOW_UP_ESCALATED_REGIMEN",
        "T5_C_ESCALATED_REGIMEN_BP_TARGET_NOT_REACHED",
        True,
    ),
    _entered(T5, "T5_C_ESCALATED_REGIMEN_BP_TARGET_NOT_REACHED"),
    _candidate(
        T5,
        "T5_C_ESCALATED_REGIMEN_BP_TARGET_NOT_REACHED",
        "T5_INF_RESISTANT_HYPERTENSION_TREATMENT_STEP",
        True,
    ),
    _entered(T5, "T5_INF_RESISTANT_HYPERTENSION_TREATMENT_STEP"),
    _candidate(
        T5,
        "T5_INF_RESISTANT_HYPERTENSION_TREATMENT_STEP",
        "T5_LINK_RESISTANT_HYPERTENSION",
        True,
    ),
    _entered(T5, "T5_LINK_RESISTANT_HYPERTENSION"),
]


@dataclass(frozen=True)
class SeededTrees:
    repository: SqlAlchemyTreeGraphRepository
    graphs: dict[str, TreeGraph]


@pytest.fixture(scope="module")
def seeded_trees(seeded_session: Session) -> SeededTrees:
    repository = SqlAlchemyTreeGraphRepository(seeded_session)
    return SeededTrees(
        repository=repository,
        graphs={tree_key: repository.get_tree(tree_key) for tree_key in TREE_KEYS},
    )


@pytest.fixture
def active_bp_target() -> dict[str, Any]:
    return deepcopy(ACTIVE_BP_TARGET)


def test_tree_1_normal_bp_route(seeded_trees: SeededTrees) -> None:
    runtime_input = {
        "clinic_1_sbp": 120,
        "clinic_1_dbp": 80,
        "clinic_2_sbp": 120,
        "clinic_2_dbp": 80,
        "clinic_3_sbp": 120,
        "clinic_3_dbp": 80,
    }

    result = walk_tree(seeded_trees.graphs[T1], runtime_input, repository=seeded_trees.repository)

    assert result.context == {"diagnosis": {"hypertension_class": "NORMAL_BP"}}
    assert result.actions == []
    _assert_trace(
        result,
        [
            _entered(T1, "T1_START_PATIENT_INFORMATION"),
            _candidate(T1, "T1_START_PATIENT_INFORMATION", "T1_C_CLINIC_1_CRISIS", False),
            _candidate(T1, "T1_START_PATIENT_INFORMATION", "T1_C_CLINIC_1_NON_CRISIS", True),
            _entered(T1, "T1_C_CLINIC_1_NON_CRISIS"),
            _candidate(T1, "T1_C_CLINIC_1_NON_CRISIS", "T1_C_CLINIC_2_DIRECT_RANGE", False),
            _candidate(T1, "T1_C_CLINIC_1_NON_CRISIS", "T1_C_CLINIC_2_LOWER", True),
            _entered(T1, "T1_C_CLINIC_2_LOWER"),
            _candidate(T1, "T1_C_CLINIC_2_LOWER", "T1_C_OPTIMAL_MEASUREMENT_ROUTE", False),
            _candidate(T1, "T1_C_CLINIC_2_LOWER", "T1_C_ESSENTIAL_MEASUREMENT_ROUTE", True),
            _entered(T1, "T1_C_ESSENTIAL_MEASUREMENT_ROUTE"),
            _candidate(T1, "T1_C_ESSENTIAL_MEASUREMENT_ROUTE", "T1_C_CLINIC_3_AVAILABLE", True),
            _entered(T1, "T1_C_CLINIC_3_AVAILABLE"),
            _candidate(T1, "T1_C_CLINIC_3_AVAILABLE", "T1_C_ESSENTIAL_HYPERTENSION", False),
            _candidate(T1, "T1_C_CLINIC_3_AVAILABLE", "T1_C_ESSENTIAL_HIGH_NORMAL_BP", False),
            _candidate(T1, "T1_C_CLINIC_3_AVAILABLE", "T1_C_ESSENTIAL_NORMAL_BP", True),
            _entered(T1, "T1_C_ESSENTIAL_NORMAL_BP"),
            _candidate(T1, "T1_C_ESSENTIAL_NORMAL_BP", "T1_END_ESSENTIAL_NORMAL_BP", True),
            _entered(T1, "T1_END_ESSENTIAL_NORMAL_BP"),
        ],
    )
    _assert_references(
        result,
        [
            (T1, "T1_C_CLINIC_1_NON_CRISIS", 1),
            (T1, "T1_C_CLINIC_1_NON_CRISIS", 2),
            (T1, "T1_C_CLINIC_2_LOWER", 1),
            (T1, "T1_C_CLINIC_2_LOWER", 2),
            (T1, "T1_C_ESSENTIAL_MEASUREMENT_ROUTE", 1),
            (T1, "T1_C_CLINIC_3_AVAILABLE", 1),
            (T1, "T1_C_ESSENTIAL_NORMAL_BP", 1),
            (T1, "T1_C_ESSENTIAL_NORMAL_BP", 2),
            (T1, "T1_END_ESSENTIAL_NORMAL_BP", 1),
            (T1, "T1_END_ESSENTIAL_NORMAL_BP", 2),
        ],
    )


def test_tree_1_emergency_route_preserves_partial_state(seeded_trees: SeededTrees) -> None:
    runtime_input = {"clinic_1_sbp": 180, "clinic_1_dbp": 80}

    with pytest.raises(LinkTargetNotFound) as exc_info:
        walk_tree(seeded_trees.graphs[T1], runtime_input, repository=seeded_trees.repository)

    error = exc_info.value
    assert error.details["link_target_tree_key"] == "hypertensive-emergency"
    state = _partial_state(error.partial_run_state)
    assert state.input_snapshot == runtime_input
    assert state.context == {"diagnosis": {"hypertension_class": "HYPERTENSIVE_EMERGENCY"}}
    assert state.actions == []
    _assert_trace(
        state,
        [
            _entered(T1, "T1_START_PATIENT_INFORMATION"),
            _candidate(T1, "T1_START_PATIENT_INFORMATION", "T1_C_CLINIC_1_CRISIS", True),
            _entered(T1, "T1_C_CLINIC_1_CRISIS"),
            _candidate(T1, "T1_C_CLINIC_1_CRISIS", "T1_INF_HYPERTENSIVE_EMERGENCY", True),
            _entered(T1, "T1_INF_HYPERTENSIVE_EMERGENCY"),
            _candidate(
                T1,
                "T1_INF_HYPERTENSIVE_EMERGENCY",
                "T1_LINK_HYPERTENSIVE_EMERGENCY",
                True,
            ),
            _entered(T1, "T1_LINK_HYPERTENSIVE_EMERGENCY"),
        ],
    )
    _assert_references(
        state,
        [
            (T1, "T1_C_CLINIC_1_CRISIS", 1),
            (T1, "T1_C_CLINIC_1_CRISIS", 2),
            (T1, "T1_INF_HYPERTENSIVE_EMERGENCY", 1),
        ],
    )


def test_tree_3_lifestyle_follow_up_meets_stored_10_5_rule(
    seeded_trees: SeededTrees,
) -> None:
    runtime_input = {
        "is_medication_follow_up": False,
        "is_lifestyle_follow_up": True,
        "pre_lifestyle_clinic_sbp": 150,
        "pre_lifestyle_clinic_dbp": 95,
        "current_clinic_sbp": 140,
        "current_clinic_dbp": 90,
    }

    result = walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    assert result.context == {}
    assert [(action.node_key, action.text_vi, action.payload) for action in result.actions] == [
        (
            "T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING",
            "Tiếp tục thay đổi lối sống và theo dõi",
            {
                "action_type": "CONTINUE_LIFESTYLE_AND_MONITORING",
                "follow_up_mode": "NEW_ENCOUNTER",
                "follow_up_required": True,
                "lifestyle_response_threshold_mmhg": {
                    "minimum_dbp_reduction": 5,
                    "minimum_sbp_reduction": 10,
                    "require_both": True,
                },
                "restart_tree_key": T1,
                "rule_origin": "LOCAL_PROJECT_POLICY",
            },
        )
    ]
    _assert_trace(
        result,
        [
            _entered(T3, "T3_START_BP_AND_AGE_INFORMATION"),
            _candidate(
                T3, "T3_START_BP_AND_AGE_INFORMATION", "T3_C_IS_MEDICATION_FOLLOW_UP", False
            ),
            _candidate(T3, "T3_START_BP_AND_AGE_INFORMATION", "T3_C_IS_LIFESTYLE_FOLLOW_UP", True),
            _entered(T3, "T3_C_IS_LIFESTYLE_FOLLOW_UP"),
            _candidate(
                T3,
                "T3_C_IS_LIFESTYLE_FOLLOW_UP",
                "T3_C_LIFESTYLE_RESPONSE_ADEQUATE",
                True,
            ),
            _entered(T3, "T3_C_LIFESTYLE_RESPONSE_ADEQUATE"),
            _candidate(
                T3,
                "T3_C_LIFESTYLE_RESPONSE_ADEQUATE",
                "T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING",
                True,
            ),
            _entered(T3, "T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING"),
        ],
    )
    _assert_references(
        result,
        [
            (T3, "T3_C_IS_LIFESTYLE_FOLLOW_UP", 1),
            (T3, "T3_C_LIFESTYLE_RESPONSE_ADEQUATE", 1),
            (T3, "T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING", 1),
        ],
    )


def test_tree_3_medication_follow_up_restores_and_uses_target(
    seeded_trees: SeededTrees,
    active_bp_target: dict[str, Any],
) -> None:
    runtime_input = _medication_input(active_bp_target, facility="FULL_RESOURCES")

    result = walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    assert result.context == {"treatment": {"bp_target": active_bp_target}}
    assert result.input_snapshot["active_bp_target"] == active_bp_target
    restore_entry = next(
        entry
        for entry in result.trace
        if entry.event is TraceEvent.NODE_ENTERED
        and entry.node_key == "T3_INF_RESTORE_ACTIVE_BP_TARGET"
    )
    assert restore_entry.changed_context_paths == ["context.treatment.bp_target"]
    target_evaluation = next(
        entry
        for entry in result.trace
        if entry.candidate_node_key == "T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED"
    )
    details = cast(dict[str, Any], target_evaluation.evaluation_details)
    children = cast(list[dict[str, Any]], details["children"])
    assert [child["right"]["value"] for child in children] == [130, 80]
    assert [
        (action.node_key, action.text_vi, action.payload["action_type"])
        for action in result.actions
    ] == [
        (
            "T5_END_INITIAL_REGIMEN_TARGET_REACHED",
            "Tiếp tục theo dõi và duy trì phác đồ",
            "CONTINUE_MONITORING_AND_MAINTAIN_REGIMEN",
        )
    ]
    _assert_trace(result, [*T3_MEDICATION_FULL_RESOURCES, *T5_INITIAL_TARGET_REACHED])
    _assert_references(result, [(T5, "T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED", 1)])


def test_tree_4_target_reached_emits_maintain_regimen_action(
    seeded_trees: SeededTrees,
    active_bp_target: dict[str, Any],
) -> None:
    runtime_input = _medication_input(active_bp_target, facility="LIMITED_RESOURCES")

    result = walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    assert result.context == {"treatment": {"bp_target": active_bp_target}}
    assert [
        (action.tree_key, action.node_key, action.text_vi, action.payload)
        for action in result.actions
    ] == [
        (
            T4,
            "T4_END_MAINTAIN_REGIMEN",
            "Tiếp tục theo dõi và duy trì phác đồ",
            {
                "action_type": "MAINTAIN_CURRENT_REGIMEN",
                "follow_up_mode": "NEW_ENCOUNTER",
                "follow_up_required": True,
                "next_medication_follow_up_stage": "INITIAL_REGIMEN",
            },
        )
    ]
    _assert_trace(result, [*T3_MEDICATION_LIMITED_RESOURCES, *T4_INITIAL_TARGET_REACHED])
    _assert_references(result, [(T4, "T4_C_INITIAL_REGIMEN_BP_TARGET_REACHED", 1)])


def test_tree_5_initial_regimen_not_reached_preserves_action_and_state(
    seeded_trees: SeededTrees,
    active_bp_target: dict[str, Any],
) -> None:
    runtime_input = _medication_input(
        active_bp_target,
        facility="FULL_RESOURCES",
        current_sbp=130,
        current_dbp=80,
    )

    with pytest.raises(LinkTargetNotFound) as exc_info:
        walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    error = exc_info.value
    assert error.details["link_target_tree_key"] == "drug-combination"
    state = _partial_state(error.partial_run_state)
    assert state.input_snapshot == runtime_input
    assert state.context == {"treatment": {"bp_target": active_bp_target}}
    assert [
        (action.tree_key, action.node_key, action.text_vi, action.payload)
        for action in state.actions
    ] == [
        (
            T5,
            "T5_ACTION_FIXED_DOSE_THREE_DRUG_COMBINATION",
            "VIÊN PHỐI HỢP 3 THUỐC (1 viên): A+C+D",
            {
                "action_type": "FIXED_DOSE_THREE_DRUG_COMBINATION",
                "classes": ["A", "C", "D"],
                "fixed_dose_combination": True,
                "follow_up_mode": "NEW_ENCOUNTER",
                "follow_up_required": True,
                "next_medication_follow_up_stage": "ESCALATED_REGIMEN",
                "pill_count": 1,
                "requires_clinician_review": True,
            },
        )
    ]
    _assert_trace(state, [*T3_MEDICATION_FULL_RESOURCES, *T5_INITIAL_TARGET_NOT_REACHED])
    _assert_references(state, [(T5, "T5_ACTION_FIXED_DOSE_THREE_DRUG_COMBINATION", 1)])


def test_tree_5_escalated_regimen_not_reached_preserves_resistant_state(
    seeded_trees: SeededTrees,
    active_bp_target: dict[str, Any],
) -> None:
    runtime_input = _medication_input(
        active_bp_target,
        facility="FULL_RESOURCES",
        stage="ESCALATED_REGIMEN",
        current_sbp=130,
        current_dbp=80,
    )

    with pytest.raises(LinkTargetNotFound) as exc_info:
        walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    error = exc_info.value
    assert error.details["link_target_tree_key"] == "resistant-hypertension"
    state = _partial_state(error.partial_run_state)
    assert state.input_snapshot == runtime_input
    assert state.context == {
        "treatment": {
            "additional_options": [
                "MRA",
                "ANOTHER_DIURETIC",
                "ALPHA_BLOCKER",
                "BETA_BLOCKER",
            ],
            "bp_target": active_bp_target,
            "pill_count": 2,
            "status": "RESISTANT_HYPERTENSION",
        }
    }
    assert state.actions == []
    _assert_trace(state, [*T3_MEDICATION_FULL_RESOURCES, *T5_ESCALATED_TARGET_NOT_REACHED])
    _assert_references(state, [(T5, "T5_INF_RESISTANT_HYPERTENSION_TREATMENT_STEP", 1)])


def _medication_input(
    active_bp_target: dict[str, Any],
    *,
    facility: str,
    stage: str = "INITIAL_REGIMEN",
    current_sbp: int = 129,
    current_dbp: int = 79,
) -> dict[str, Any]:
    return {
        "is_medication_follow_up": True,
        "facility_capability": facility,
        "medication_follow_up_stage": stage,
        "active_bp_target": active_bp_target,
        "current_clinic_sbp": current_sbp,
        "current_clinic_dbp": current_dbp,
    }


def _partial_state(state: RunState | None) -> RunState:
    assert state is not None
    return state


def _assert_trace(
    state: RunState | TraversalResult,
    expected: list[TraceSignature],
) -> None:
    assert [entry.step for entry in state.trace] == list(range(1, len(expected) + 1))
    assert [
        (
            entry.event.value,
            entry.tree_key,
            entry.node_key,
            entry.candidate_node_key,
            entry.condition_result,
        )
        for entry in state.trace
    ] == expected


def _assert_references(
    state: RunState | TraversalResult,
    expected: list[ReferenceSignature],
) -> None:
    assert [
        (reference.tree_key, reference.node_key, reference.reference_order)
        for reference in state.references
    ] == expected
    assert all(reference.source_title for reference in state.references)
    assert all(reference.section_path for reference in state.references)
