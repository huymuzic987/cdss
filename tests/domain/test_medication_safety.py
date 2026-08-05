from __future__ import annotations

from typing import Any
from uuid import UUID

from cdss.domain.decision_tree import Medicine, NodeDefinition, NodeType, RunState, collect_action
from cdss.domain.medication_safety import evaluate_medication_safety, evaluate_target
from cdss.domain.medication_safety_resolver import filter_medicine_options


def _fact(status: str, value: Any = None) -> dict[str, Any]:
    return {"status": status, "value": value, "evidence": [{"source": "test"}]}


def _runtime(**facts: dict[str, Any]) -> dict[str, Any]:
    return {"clinical_facts": facts}


def _medicine(name: str, drug_class: str, subgroup: str) -> Medicine:
    return Medicine(
        drug_id=name,
        name=name,
        drug_class=drug_class,
        subgroup=subgroup,
        route="Thuốc Uống",
        dose_low="1 mg",
        dose_usual="2 mg",
        dose_max="4 mg",
        source="test",
        link=None,
        available=True,
    )


def test_pregnancy_blocks_ace_arb_and_direct_renin_but_keeps_dhp_as_candidate() -> None:
    runtime = _runtime(pregnancy_status=_fact("present", True))
    options, profile = filter_medicine_options(
        [
            {
                "classes": ["A", "C"],
                "medicines": {
                    "A": [
                        {"name": "Enalapril", "drug_class": "A", "subgroup": "ACE"},
                        {"name": "Losartan", "drug_class": "A", "subgroup": "ARB"},
                    ],
                    "C": [{"name": "Amlodipine", "drug_class": "C", "subgroup": "DHP"}],
                },
            }
        ],
        runtime,
    )

    assert options == []
    assert "ACE_INHIBITOR" in profile["blocked_targets"]
    assert "ARB" in profile["blocked_targets"]


def test_mra_requires_known_safe_potassium_and_egfr() -> None:
    option = [
        {
            "classes": ["MRA"],
            "medicines": {
                "MRA": [{"name": "Spironolactone", "drug_class": "D", "subgroup": "MRA"}]
            },
        }
    ]
    missing, missing_profile = filter_medicine_options(option, _runtime())
    unsafe, unsafe_profile = filter_medicine_options(
        option,
        _runtime(
            serum_potassium=_fact("present", 4.6),
            eGFR=_fact("present", 55),
        ),
    )

    assert missing == []
    assert missing_profile["status"] == "NEEDS_REVIEW"
    assert unsafe == []
    assert "MRA" in unsafe_profile["blocked_targets"]


def test_conflicting_facts_require_review_and_current_therapy_is_not_silently_removed() -> None:
    runtime = _runtime(
        eGFR={"status": "conflicting", "evidence": [{"source": "HIS"}, {"source": "manual"}]}
    )
    runtime["active_medication_regimen"] = [
        {"name": "Enalapril", "drug_class": "A", "subgroup": "ACE"}
    ]
    profile = evaluate_medication_safety(runtime, medicines=runtime["active_medication_regimen"])

    assert profile["status"] == "NEEDS_REVIEW"
    assert profile["findings"] == []
    assert runtime["active_medication_regimen"]


def test_active_regimen_dual_ras_blockade_is_an_interaction_finding() -> None:
    runtime = _runtime()
    profile = evaluate_medication_safety(
        runtime,
        medicines=[
            {"name": "Enalapril", "drug_class": "A"},
            {"name": "Losartan", "drug_class": "A"},
        ],
    )

    assert any(
        item["reason_code"] == "DUAL_RAS_BLOCKADE" for item in profile["findings"]
    )
    assert "RAS_COMBINATION" in profile["blocked_targets"]


def test_stable_asthma_is_relative_for_cardioselective_beta_blocker() -> None:
    runtime = _runtime(asthma_severity=_fact("present", "stable"))
    cardioselective = evaluate_target(
        "B", runtime, medicine=_medicine("Bisoprolol", "B", "Beta-1 selective")
    )
    nonselective = evaluate_target("B", runtime, medicine=_medicine("Propranolol", "B", "Beta"))

    assert cardioselective["status"] == "RELATIVE"
    assert nonselective["status"] == "ABSOLUTE"


class _Repository:
    def __init__(self, medicines: tuple[Medicine, ...]) -> None:
        self.medicines = medicines

    def get_by_id(self, drug_id: str) -> Medicine | None:
        return next((item for item in self.medicines if item.drug_id == drug_id), None)

    def list_by_class(self, drug_class: str) -> tuple[Medicine, ...]:
        return tuple(item for item in self.medicines if item.drug_class == drug_class)

    def list_all(self) -> tuple[Medicine, ...]:
        return self.medicines


def test_action_gate_can_stop_tree_6_without_being_reached_by_a_global_node() -> None:
    node = NodeDefinition(
        id=UUID(int=1),
        tree_id=UUID(int=2),
        node_key="recommendation",
        node_type=NodeType.END,
        text_en="Start combination",
        text_vi="",
        action_payload={"action_type": "INITIAL_TWO_DRUG_COMBINATION"},
    )
    state = RunState.initialize(
        _runtime(pregnancy_status=_fact("present", True)) | {"active_medication_regimen": []}
    )
    state.context["treatment_preferences"] = {
        "combination_options": [["A", "C"]],
    }
    repository = _Repository(
        (
            _medicine("Enalapril", "A", "ACE"),
            _medicine("Amlodipine", "C", "DHP"),
        )
    )

    action = collect_action(
        node, state, tree_key="drug-combination", medicine_repository=repository
    )

    assert action is not None
    assert action.payload["action_type"] == "NO_SAFE_OPTION"
    assert action.payload["medicine_options"] == []


def test_maintain_action_reports_current_contraindicated_regimen_for_review() -> None:
    node = NodeDefinition(
        id=UUID(int=3),
        tree_id=UUID(int=4),
        node_key="maintain",
        node_type=NodeType.END,
        text_en="Maintain current regimen",
        text_vi="",
        action_payload={"action_type": "MAINTAIN_CURRENT_REGIMEN"},
    )
    runtime = _runtime(pregnancy_status=_fact("present", True))
    runtime["active_medication_regimen"] = [
        {"name": "Enalapril", "drug_class": "A", "status": "active"}
    ]
    state = RunState.initialize(runtime)

    action = collect_action(
        node, state, tree_key="drug-combination", medicine_repository=_Repository(())
    )

    assert action is not None
    assert action.payload["current_regimen_review_required"] is True
    assert action.payload["current_regimen_safety"]["blocked_targets"] == ["ACE_INHIBITOR"]
