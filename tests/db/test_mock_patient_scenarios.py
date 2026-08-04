"""Deterministic read-only patient routes derived from the seeded Trees 1-5."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session

from cdss.domain.decision_tree import (
    MissingRuntimePath,
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
    _candidate(T3, "T3_C_IS_MEDICATION_FOLLOW_UP", "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET", True),
    _entered(T3, "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET"),
    _candidate(
        T3,
        "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET",
        "T3_LINK_ESSENTIAL_TREATMENT_STRATEGY",
        False,
    ),
    _candidate(
        T3,
        "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET",
        "T3_LINK_OPTIMAL_TREATMENT_STRATEGY",
        True,
    ),
    _entered(T3, "T3_LINK_OPTIMAL_TREATMENT_STRATEGY"),
]

T3_MEDICATION_LIMITED_RESOURCES = [
    _entered(T3, "T3_START_BP_AND_AGE_INFORMATION"),
    _candidate(T3, "T3_START_BP_AND_AGE_INFORMATION", "T3_C_IS_MEDICATION_FOLLOW_UP", True),
    _entered(T3, "T3_C_IS_MEDICATION_FOLLOW_UP"),
    _candidate(T3, "T3_C_IS_MEDICATION_FOLLOW_UP", "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET", True),
    _entered(T3, "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET"),
    _candidate(
        T3,
        "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET",
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
        "T5_INFERENCE_COMBINE_FIXED_DOSE_A_C_D_ONE_PILL",
        True,
    ),
    _entered(T5, "T5_INFERENCE_COMBINE_FIXED_DOSE_A_C_D_ONE_PILL"),
    _candidate(
        T5,
        "T5_INFERENCE_COMBINE_FIXED_DOSE_A_C_D_ONE_PILL",
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
        "T5_INFERENCE_SELECT_MRA_OR_ANOTHER_DIURETIC_OR_ALPHA_BLOCKER_OR_BETA_BLOCKER_FOR_RESISTANT_HYPERTENSION",
        True,
    ),
    _entered(
        T5,
        "T5_INFERENCE_SELECT_MRA_OR_ANOTHER_DIURETIC_OR_ALPHA_BLOCKER_OR_BETA_BLOCKER_FOR_RESISTANT_HYPERTENSION",
    ),
    _candidate(
        T5,
        "T5_INFERENCE_SELECT_MRA_OR_ANOTHER_DIURETIC_OR_ALPHA_BLOCKER_OR_BETA_BLOCKER_FOR_RESISTANT_HYPERTENSION",
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
        "is_pregnant": False,
        "is_postpartum": False,
        "current_clinic_sbp": 120,
        "current_clinic_dbp": 80,
    }

    result = walk_tree(seeded_trees.graphs[T1], runtime_input, repository=seeded_trees.repository)

    assert result.context == {
        "diagnosis": {
            "hypertension_class": "NORMAL_BP",
            "current_clinic_sbp": 120,
            "current_clinic_dbp": 80,
        }
    }
    assert result.actions == []
    _assert_trace(
        result,
        [
            _entered(T1, "T1_START_PATIENT_INFORMATION"),
            _candidate(T1, "T1_START_PATIENT_INFORMATION", "T1_C_IS_PREGNANT", False),
            _candidate(T1, "T1_START_PATIENT_INFORMATION", "T1_C_IS_NOT_PREGNANT", True),
            _entered(T1, "T1_C_IS_NOT_PREGNANT"),
            _candidate(T1, "T1_C_IS_NOT_PREGNANT", "T1_C_CLINIC_1_CRISIS", False),
            _candidate(T1, "T1_C_IS_NOT_PREGNANT", "T1_C_CLINIC_1_NON_CRISIS", True),
            _entered(T1, "T1_C_CLINIC_1_NON_CRISIS"),
            _candidate(T1, "T1_C_CLINIC_1_NON_CRISIS", "T1_C_ESSENTIAL_HYPERTENSION", False),
            _candidate(T1, "T1_C_CLINIC_1_NON_CRISIS", "T1_C_ESSENTIAL_HIGH_NORMAL_BP", False),
            _candidate(T1, "T1_C_CLINIC_1_NON_CRISIS", "T1_C_ESSENTIAL_NORMAL_BP", True),
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
            (T1, "T1_C_ESSENTIAL_NORMAL_BP", 1),
            (T1, "T1_C_ESSENTIAL_NORMAL_BP", 2),
            (T1, "T1_END_ESSENTIAL_NORMAL_BP", 1),
            (T1, "T1_END_ESSENTIAL_NORMAL_BP", 2),
        ],
    )


def test_tree_1_emergency_route_now_needs_pregnancy_status(
    seeded_trees: SeededTrees,
) -> None:
    """hypertensive-emergency is now seeded (backups/cdss_merged.sql). Its crisis
    check itself reads `input.is_pregnant` (pregnancy-adjusted thresholds), and the
    evaluator reads every `any`/`all` child rather than short-circuiting, so this
    fixture (which never had to supply that field for Trees 1-5) now fails at the
    very first candidate evaluation from T1_START, before even reaching the LINK.
    """
    runtime_input = {"current_clinic_sbp": 180, "current_clinic_dbp": 80}

    with pytest.raises(MissingRuntimePath) as exc_info:
        walk_tree(seeded_trees.graphs[T1], runtime_input, repository=seeded_trees.repository)

    error = exc_info.value
    assert error.details["path"] == "input.is_pregnant"
    state = _partial_state(error.partial_run_state)
    assert state.input_snapshot == runtime_input
    assert state.context == {
        "diagnosis": {
            "current_clinic_sbp": 180,
            "current_clinic_dbp": 80,
        }
    }
    assert state.actions == []
    _assert_trace(
        state,
        [
            _entered(T1, "T1_START_PATIENT_INFORMATION"),
        ],
    )
    _assert_references(state, [])


def test_tree_3_lifestyle_follow_up_meets_stored_15_10_rule(
    seeded_trees: SeededTrees,
) -> None:
    runtime_input = {
        "is_medication_follow_up": False,
        "is_lifestyle_follow_up": True,
        "previous_sbp": 150,
        "previous_dbp": 95,
        "current_clinic_sbp": 135,
        "current_clinic_dbp": 85,
    }

    result = walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    assert result.context == {
        "diagnosis": {
            "current_clinic_sbp": 135,
            "current_clinic_dbp": 85,
        }
    }
    assert [(action.node_key, action.text_vi, action.payload) for action in result.actions] == [
        (
            "T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING",
            "Tiếp tục thay đổi lối sống và theo dõi",
            {
                "action_type": "CONTINUE_LIFESTYLE_AND_MONITORING",
                "follow_up_mode": "NEW_ENCOUNTER",
                "follow_up_required": True,
                "lifestyle_response_threshold_mmhg": {
                    "minimum_dbp_reduction": 10,
                    "minimum_sbp_reduction": 15,
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

    assert result.context == {
        "treatment": {"bp_target": active_bp_target},
        "diagnosis": {
            "current_clinic_sbp": 129,
            "current_clinic_dbp": 79,
        },
    }
    assert result.input_snapshot["active_bp_target"] == active_bp_target
    restore_entry = next(
        entry
        for entry in result.trace
        if entry.event is TraceEvent.NODE_ENTERED
        and entry.node_key == "T3_INFERENCE_RESTORE_ACTIVE_BP_TARGET"
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

    assert result.context == {
        "treatment": {"bp_target": active_bp_target},
        "diagnosis": {
            "current_clinic_sbp": 129,
            "current_clinic_dbp": 79,
        },
    }
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


DRUG_COMBINATION_STARTED_MISSING_HEART_FAILURE_INPUT = [
    _entered("drug-combination", "T6_START_PATIENT_INFO_AND_PRESCRIPTIONS"),
    _candidate(
        "drug-combination", "T6_START_PATIENT_INFO_AND_PRESCRIPTIONS", "T6_C_FIRST_VISIT", False
    ),
    _candidate(
        "drug-combination",
        "T6_START_PATIENT_INFO_AND_PRESCRIPTIONS",
        "T6_C_FOLLOW_UP_VISIT",
        True,
    ),
    _entered("drug-combination", "T6_C_FOLLOW_UP_VISIT"),
    _candidate(
        "drug-combination",
        "T6_C_FOLLOW_UP_VISIT",
        "T6_INFERENCE_DETERMINE_PRIOR_PRESCRIPTION_STATUS",
        True,
    ),
    _entered("drug-combination", "T6_INFERENCE_DETERMINE_PRIOR_PRESCRIPTION_STATUS"),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_DETERMINE_PRIOR_PRESCRIPTION_STATUS",
        "T6_C_HAS_PRIOR_PRESCRIPTION",
        True,
    ),
    _entered("drug-combination", "T6_C_HAS_PRIOR_PRESCRIPTION"),
    _candidate(
        "drug-combination",
        "T6_C_HAS_PRIOR_PRESCRIPTION",
        "T6_INFERENCE_COMPARE_WITH_CURRENT_PRESCRIPTION",
        True,
    ),
    _entered("drug-combination", "T6_INFERENCE_COMPARE_WITH_CURRENT_PRESCRIPTION"),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_COMPARE_WITH_CURRENT_PRESCRIPTION",
        "T6_C_DOSAGE_ADJUSTMENT_REQUESTED",
        False,
    ),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_COMPARE_WITH_CURRENT_PRESCRIPTION",
        "T6_C_NO_DOSAGE_ADJUSTMENT_REQUESTED",
        True,
    ),
    _entered("drug-combination", "T6_C_NO_DOSAGE_ADJUSTMENT_REQUESTED"),
    _candidate(
        "drug-combination",
        "T6_C_NO_DOSAGE_ADJUSTMENT_REQUESTED",
        "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_ADJUSTMENT",
        True,
    ),
    _entered(
        "drug-combination", "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_ADJUSTMENT"
    ),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_ADJUSTMENT",
        "T6_INFERENCE_DETERMINE_CONTRAINDICATIONS",
        True,
    ),
    _entered("drug-combination", "T6_INFERENCE_DETERMINE_CONTRAINDICATIONS"),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_DETERMINE_CONTRAINDICATIONS",
        "T6_C_HAS_DUPLICATE_DRUG_CLASS",
        False,
    ),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_DETERMINE_CONTRAINDICATIONS",
        "T6_C_NO_DUPLICATE_DRUG_CLASS",
        True,
    ),
    _entered("drug-combination", "T6_C_NO_DUPLICATE_DRUG_CLASS"),
    _candidate(
        "drug-combination",
        "T6_C_NO_DUPLICATE_DRUG_CLASS",
        "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_DUPLICATE",
        True,
    ),
    _entered(
        "drug-combination", "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_DUPLICATE"
    ),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_DUPLICATE",
        "T6_C_IS_FIRST_VISIT_FOR_REGIMEN",
        False,
    ),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_DUPLICATE",
        "T6_C_IS_FOLLOW_UP_FOR_REGIMEN",
        True,
    ),
    _entered("drug-combination", "T6_C_IS_FOLLOW_UP_FOR_REGIMEN"),
    _candidate("drug-combination", "T6_C_IS_FOLLOW_UP_FOR_REGIMEN", "T6_C_TARGET_ACHIEVED", False),
    _candidate(
        "drug-combination", "T6_C_IS_FOLLOW_UP_FOR_REGIMEN", "T6_C_TARGET_NOT_ACHIEVED", True
    ),
    _entered("drug-combination", "T6_C_TARGET_NOT_ACHIEVED"),
    _candidate(
        "drug-combination",
        "T6_C_TARGET_NOT_ACHIEVED",
        "T6_C_FOLLOWUP_INITIAL_STAGE",
        True,
    ),
    _entered("drug-combination", "T6_C_FOLLOWUP_INITIAL_STAGE"),
    _candidate(
        "drug-combination",
        "T6_C_FOLLOWUP_INITIAL_STAGE",
        "T6_INFERENCE_DETERMINE_PRIOR_REGIMEN_INTENSITY",
        True,
    ),
    _entered("drug-combination", "T6_INFERENCE_DETERMINE_PRIOR_REGIMEN_INTENSITY"),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_DETERMINE_PRIOR_REGIMEN_INTENSITY",
        "T6_C_WAS_ON_MONOTHERAPY",
        False,
    ),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_DETERMINE_PRIOR_REGIMEN_INTENSITY",
        "T6_C_WAS_NOT_ON_MONOTHERAPY",
        True,
    ),
    _entered("drug-combination", "T6_C_WAS_NOT_ON_MONOTHERAPY"),
    _candidate(
        "drug-combination",
        "T6_C_WAS_NOT_ON_MONOTHERAPY",
        "T6_INFERENCE_ESCALATE_TWO_DRUG_DOSE_OR_COMBINE_A_C_AND_D",
        True,
    ),
    _entered("drug-combination", "T6_INFERENCE_ESCALATE_TWO_DRUG_DOSE_OR_COMBINE_A_C_AND_D"),
    _candidate(
        "drug-combination",
        "T6_INFERENCE_ESCALATE_TWO_DRUG_DOSE_OR_COMBINE_A_C_AND_D",
        "T6_INFERENCE_DETERMINE_SPECIFIC_CLINICAL_FLAGS_ESCALATION",
        True,
    ),
    _entered("drug-combination", "T6_INFERENCE_DETERMINE_SPECIFIC_CLINICAL_FLAGS_ESCALATION"),
]


def test_tree_5_initial_regimen_not_reached_resolves_link_then_needs_more_input(
    seeded_trees: SeededTrees,
    active_bp_target: dict[str, Any],
) -> None:
    """drug-combination is now seeded (backups/cdss_merged.sql), so the LINK resolves
    and traversal continues into it, working through several of its own INFERENCE
    nodes, until it fails on a required field (`has_heart_failure`) this fixture
    never had to supply for Trees 1-5, instead of raising LinkTargetNotFound.
    """
    runtime_input = _medication_input(
        active_bp_target,
        facility="FULL_RESOURCES",
        current_sbp=130,
        current_dbp=80,
    )

    with pytest.raises(MissingRuntimePath) as exc_info:
        walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    error = exc_info.value
    assert error.details["path"] == "input.has_heart_failure"
    state = _partial_state(error.partial_run_state)
    assert state.input_snapshot == runtime_input
    assert state.context == {
        "treatment": {
            "bp_target": active_bp_target,
            "has_prior_prescription": True,
            "has_dosage_adjustment_request": False,
            "has_duplicate_drug_class": False,
            "has_duplicate_ras_inhibitor": False,
            "was_on_monotherapy": False,
            "has_angina": False,
            "has_prior_mi": False,
            "has_atrial_fibrillation": False,
            "has_tachycardia": False,
            "is_pregnant": False,
        },
        "diagnosis": {
            "current_clinic_sbp": 130,
            "current_clinic_dbp": 80,
        },
        "treatment_preferences": {
            "escalation_options": [
                {"strategy": "INCREASE_DOSE_TWO_DRUG"},
                {"strategy": "THREE_DRUG_COMBINATION", "classes": ["A", "C", "D"]},
            ],
        },
    }
    # The canonical seed normalizes prescribing steps into INFERENCE nodes.
    # They update regimen context but are not collected as terminal actions.
    assert state.actions == []
    _assert_trace(
        state,
        [
            *T3_MEDICATION_FULL_RESOURCES,
            *T5_INITIAL_TARGET_NOT_REACHED,
            *DRUG_COMBINATION_STARTED_MISSING_HEART_FAILURE_INPUT,
        ],
    )
    _assert_references(
        state,
        [
            (T5, "T5_INFERENCE_COMBINE_FIXED_DOSE_A_C_D_ONE_PILL", 1),
            ("drug-combination", "T6_START_PATIENT_INFO_AND_PRESCRIPTIONS", 1),
            ("drug-combination", "T6_INFERENCE_DETERMINE_CONTRAINDICATIONS", 1),
            ("drug-combination", "T6_INFERENCE_DETERMINE_CONTRAINDICATIONS", 2),
            ("drug-combination", "T6_INFERENCE_ESCALATE_TWO_DRUG_DOSE_OR_COMBINE_A_C_AND_D", 1),
        ],
    )


RESISTANT_HYPERTENSION_FULL_TREATMENT = [
    _entered("resistant-hypertension", "T13_START"),
    _candidate("resistant-hypertension", "T13_START", "T13_C_LIMITED", False),
    _candidate("resistant-hypertension", "T13_START", "T13_C_FULL", True),
    _entered("resistant-hypertension", "T13_C_FULL"),
    _candidate("resistant-hypertension", "T13_C_FULL", "T13_A_CONSIDER_DEVICE", True),
    _entered("resistant-hypertension", "T13_A_CONSIDER_DEVICE"),
]


def test_tree_5_escalated_regimen_resolves_link_and_reaches_resistant_hypertension_terminal(
    seeded_trees: SeededTrees,
    active_bp_target: dict[str, Any],
) -> None:
    """The Tree 5 LINK resolves into the configured full-resource Tree 13 action."""
    runtime_input = _medication_input(
        active_bp_target,
        facility="FULL_RESOURCES",
        stage="ESCALATED_REGIMEN",
        current_sbp=130,
        current_dbp=80,
    )

    result = walk_tree(seeded_trees.graphs[T3], runtime_input, repository=seeded_trees.repository)

    assert result.context == {
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
        },
        "diagnosis": {
            "current_clinic_sbp": 130,
            "current_clinic_dbp": 80,
        },
    }
    assert [
        (action.tree_key, action.node_key, action.text_vi, action.payload)
        for action in result.actions
    ] == [
        (
            "resistant-hypertension",
            "T13_A_CONSIDER_DEVICE",
            "Xem xét điều trị can thiệp dụng cụ",
            {"action_type": "CONSIDER_DEVICE_INTERVENTION"},
        ),
    ]
    _assert_trace(
        result,
        [
            *T3_MEDICATION_FULL_RESOURCES,
            *T5_ESCALATED_TARGET_NOT_REACHED,
            *RESISTANT_HYPERTENSION_FULL_TREATMENT,
        ],
    )
    _assert_references(
        result,
        [
            (
                T5,
                "T5_INFERENCE_SELECT_MRA_OR_ANOTHER_DIURETIC_OR_ALPHA_BLOCKER_OR_BETA_BLOCKER_FOR_RESISTANT_HYPERTENSION",
                1,
            ),
            ("resistant-hypertension", "T13_START", 1),
            ("resistant-hypertension", "T13_C_FULL", 1),
            ("resistant-hypertension", "T13_A_CONSIDER_DEVICE", 1),
        ],
    )


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
