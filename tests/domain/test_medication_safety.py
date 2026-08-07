from __future__ import annotations

from typing import Any
from uuid import UUID

from cdss.domain.decision_tree import (
    EffectiveMedicationRegimen,
    MedicationRegimenPlan,
    Medicine,
    NodeDefinition,
    NodeType,
    RegimenAlternative,
    RegimenComponent,
    RegimenKeyword,
    RegimenUpdateStep,
    RunState,
    collect_action,
    filter_medication_regimen_plan,
)
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
    safe, safe_profile = filter_medicine_options(
        option,
        _runtime(
            serum_potassium=_fact("present", 4.0),
            eGFR=_fact("present", 60),
        ),
    )
    unsafe, unsafe_profile = filter_medicine_options(
        option,
        _runtime(
            serum_potassium=_fact("present", 4.6),
            eGFR=_fact("present", 55),
        ),
    )

    assert missing == []
    assert missing_profile["status"] == "NEEDS_REVIEW"
    assert safe
    assert safe_profile["status"] == "COMPLETE"
    assert unsafe == []
    assert "MRA" in unsafe_profile["blocked_targets"]


def test_safety_removed_mra_is_announced_as_a_regimen_removal() -> None:
    ras = {"drug_id": "A-1", "name": "Losartan", "drug_class": "A", "subgroup": "ARB"}
    mra = {"drug_id": "MRA-1", "name": "Eplerenone", "drug_class": "MRA", "subgroup": "MRA"}
    ras_component = RegimenComponent(selector_kind="class", code="A")
    mra_component = RegimenComponent(selector_kind="class", code="MRA")
    plan = MedicationRegimenPlan(
        steps=[
            RegimenUpdateStep(
                id="start-mra",
                trace_step=1,
                tree_key="heart-failure",
                node_key="T10_INFERENCE_COMBINE_A_MRA",
                keyword=RegimenKeyword.COMBINE,
                text_en="Combine A + MRA",
                text_vi="",
                source="structured",
                components=[ras_component, mra_component],
            )
        ],
        effective_regimen=EffectiveMedicationRegimen(
            base_options=[RegimenAlternative(components=[ras_component, mra_component])],
            status="complete",
        ),
        catalog=[ras, mra],
        catalog_by_class={"A": [ras], "MRA": [mra]},
    )

    filtered = filter_medication_regimen_plan(
        plan,
        _runtime(
            serum_potassium=_fact("present", 4.6),
            eGFR=_fact("present", 55),
        ),
    )

    assert filtered.effective_regimen.base_options == []
    assert filtered.effective_regimen.status == "partial"
    assert [item.code for item in filtered.steps[0].components] == ["A", "MRA"]
    assert filtered.steps[-1].keyword is RegimenKeyword.REMOVE
    assert filtered.steps[-1].components == [mra_component]
    assert "required medication-safety checks" in filtered.steps[-1].text_en
    assert filtered.steps[-1].warnings == ["SAFETY_REMOVED:MRA"]


def test_safety_removed_non_mra_component_is_announced_as_a_regimen_removal() -> None:
    thiazide = {
        "drug_id": "D-THIAZIDE",
        "name": "Hydrochlorothiazide",
        "drug_class": "D",
        "subgroup": "LT Thiazide",
    }
    component = RegimenComponent(selector_kind="class", code="D")
    plan = MedicationRegimenPlan(
        steps=[
            RegimenUpdateStep(
                id="start-d",
                trace_step=1,
                tree_key="hypertension",
                node_key="T5_INFERENCE_START_D",
                keyword=RegimenKeyword.START,
                text_en="Start D",
                text_vi="",
                source="structured",
                components=[component],
            )
        ],
        effective_regimen=EffectiveMedicationRegimen(
            base_options=[RegimenAlternative(components=[component])],
            status="complete",
        ),
        catalog=[thiazide],
        catalog_by_class={"D": [thiazide]},
    )

    filtered = filter_medication_regimen_plan(
        plan,
        _runtime(gout_status=_fact("present", True)),
    )

    assert [item.code for item in filtered.steps[0].components] == ["D"]
    assert filtered.steps[-1].keyword is RegimenKeyword.REMOVE
    assert [item.code for item in filtered.steps[-1].components] == ["D"]


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

    assert any(item["reason_code"] == "DUAL_RAS_BLOCKADE" for item in profile["findings"])
    assert "RAS_COMBINATION" in profile["blocked_targets"]


def test_stable_asthma_is_relative_for_cardioselective_beta_blocker() -> None:
    runtime = _runtime(asthma_severity=_fact("present", "stable"))
    cardioselective = evaluate_target(
        "B", runtime, medicine=_medicine("Bisoprolol", "B", "Beta-1 selective")
    )
    nonselective = evaluate_target("B", runtime, medicine=_medicine("Propranolol", "B", "Beta"))

    assert cardioselective["status"] == "RELATIVE"
    assert nonselective["status"] == "ABSOLUTE"


def test_gout_filters_thiazides_from_trace_derived_final_regimen() -> None:
    thiazide = {
        "drug_id": "D-THIAZIDE",
        "name": "Hydrochlorothiazide",
        "drug_class": "D",
        "subgroup": "LT Thiazide",
        "available": True,
    }
    loop_diuretic = {
        "drug_id": "D-LOOP",
        "name": "Furosemide",
        "drug_class": "D",
        "subgroup": "LT quai",
        "available": True,
    }
    plan = MedicationRegimenPlan(
        steps=[
            RegimenUpdateStep(
                id="start-d",
                trace_step=1,
                tree_key="drug-combination",
                node_key="start-d",
                keyword=RegimenKeyword.START,
                text_en="Start D",
                text_vi="",
                source="context",
                components=[RegimenComponent(selector_kind="class", code="D")],
            ),
            RegimenUpdateStep(
                id="remove-thiazide",
                trace_step=2,
                tree_key="drug-combination",
                node_key="T6_INFERENCE_DETERMINE_CONTRAINDICATIONS",
                keyword=RegimenKeyword.REMOVE,
                text_en="Remove contraindicated thiazide subgroup",
                text_vi="",
                source="context",
                components=[
                    RegimenComponent(
                        selector_kind="class",
                        code="D",
                        subgroup="LT Thiazide",
                    )
                ],
            ),
        ],
        effective_regimen=EffectiveMedicationRegimen(
            base_options=[
                RegimenAlternative(
                    components=[
                        RegimenComponent(selector_kind="class", code="A"),
                        RegimenComponent(selector_kind="class", code="C"),
                    ]
                ),
                RegimenAlternative(
                    components=[
                        RegimenComponent(selector_kind="class", code="A"),
                        RegimenComponent(selector_kind="class", code="D"),
                    ]
                ),
            ],
            additions=[RegimenComponent(selector_kind="class", code="D")],
            status="choice_required",
        ),
        catalog=[thiazide, loop_diuretic],
        catalog_by_class={"D": [thiazide, loop_diuretic]},
    )
    runtime = _runtime(gout_status=_fact("present", True))
    runtime["contraindication_findings"] = [
        {
            "target": "THIAZIDE_LIKE_DIURETIC",
            "severity": "ABSOLUTE",
            "reason_code": "GOUT",
            "drug_group": "LT Thiazide",
        }
    ]

    filtered = filter_medication_regimen_plan(plan, runtime)

    assert [item["name"] for item in filtered.catalog] == ["Furosemide"]
    assert [
        [component.code for component in option.components]
        for option in filtered.effective_regimen.base_options
    ] == [["A", "C"], ["A", "D"]]
    assert [component.code for component in filtered.effective_regimen.additions] == ["D"]
    assert filtered.steps[-1].components[0].subgroup == "LT Thiazide"
    assert [item["name"] for item in filtered.catalog_by_class["D"]] == ["Furosemide"]


def test_relative_contraindication_keeps_catalog_medicine_and_marks_warning() -> None:
    thiazide = {
        "drug_id": "D-THIAZIDE",
        "name": "Hydrochlorothiazide",
        "drug_class": "D",
        "subgroup": "LT Thiazide",
        "available": True,
    }
    loop_diuretic = {
        "drug_id": "D-LOOP",
        "name": "Furosemide",
        "drug_class": "D",
        "subgroup": "LT quai",
        "available": True,
    }
    plan = MedicationRegimenPlan(
        steps=[
            RegimenUpdateStep(
                id="start-d",
                trace_step=1,
                tree_key="drug-combination",
                node_key="start-d",
                keyword=RegimenKeyword.START,
                text_en="Start D",
                text_vi="",
                source="context",
                components=[RegimenComponent(selector_kind="class", code="D")],
            )
        ],
        effective_regimen=EffectiveMedicationRegimen(
            base_options=[
                RegimenAlternative(
                    components=[
                        RegimenComponent(selector_kind="class", code="A"),
                        RegimenComponent(selector_kind="class", code="D"),
                    ]
                )
            ],
            additions=[],
            status="complete",
        ),
        catalog=[thiazide, loop_diuretic],
        catalog_by_class={"D": [thiazide, loop_diuretic]},
    )
    runtime = _runtime()
    runtime["contraindication_findings"] = [
        {
            "target": "THIAZIDE_LIKE_DIURETIC",
            "severity": "RELATIVE",
            "reason_code": "GLUCOSE_INTOLERANCE",
            "drug_group": "LT Thiazide",
        }
    ]

    filtered = filter_medication_regimen_plan(plan, runtime)

    assert [item["name"] for item in filtered.catalog] == [
        "Hydrochlorothiazide",
        "Furosemide",
    ]
    assert filtered.catalog[0]["safety_status"] == "RELATIVE"
    assert filtered.catalog[0]["requires_override_reason"] is True
    assert "safety_findings" in filtered.catalog[0]
    assert filtered.effective_regimen.base_options[0].components[-1].code == "D"


def test_empty_filtered_class_is_not_left_in_the_final_regimen() -> None:
    b = RegimenComponent(selector_kind="class", code="B")
    removed_b = RegimenComponent(selector_kind="class", code="B", subgroup="CB")
    plan = MedicationRegimenPlan(
        steps=[
            RegimenUpdateStep(
                id="start-b",
                trace_step=1,
                tree_key="drug-combination",
                node_key="start-b",
                keyword=RegimenKeyword.START,
                text_en="Start B",
                text_vi="",
                source="context",
                components=[b],
            ),
            RegimenUpdateStep(
                id="remove-b",
                trace_step=2,
                tree_key="drug-combination",
                node_key="T6_INFERENCE_DETERMINE_CONTRAINDICATIONS",
                keyword=RegimenKeyword.REMOVE,
                text_en="Remove B",
                text_vi="",
                source="context",
                components=[removed_b],
            ),
        ],
        effective_regimen=EffectiveMedicationRegimen(
            base_options=[RegimenAlternative(components=[b])],
            additions=[],
            status="complete",
        ),
        catalog=[],
        catalog_by_class={"B": []},
    )
    runtime = _runtime()
    runtime["contraindication_findings"] = [
        {"target": "BETA_BLOCKER", "severity": "ABSOLUTE", "drug_group": "CB"}
    ]

    filtered = filter_medication_regimen_plan(plan, runtime)

    assert filtered.effective_regimen.base_options == []


def test_loop_diuretic_in_class_d_is_not_misclassified_as_thiazide() -> None:
    result = evaluate_target(
        "D",
        _runtime(gout_status=_fact("present", True)),
        medicine=_medicine("Furosemide", "D", "LT quai"),
    )

    assert result["target"] == "OTHER"
    assert result["status"] == "ELIGIBLE"


def test_d_option_keeps_safe_diuretic_subgroups_when_thiazides_are_contraindicated() -> None:
    options, profile = filter_medicine_options(
        [
            {
                "classes": ["A", "D", "SGLT2i"],
                "medicines": {
                    "A": [{"name": "Losartan", "drug_class": "A", "subgroup": "CTTA"}],
                    "D": [
                        {
                            "name": "Hydrochlorothiazide",
                            "drug_class": "D",
                            "subgroup": "LT Thiazide",
                        },
                        {
                            "name": "Furosemide",
                            "drug_class": "D",
                            "subgroup": "LT quai",
                        },
                    ],
                    "SGLT2i": [
                        {
                            "name": "Empagliflozin",
                            "drug_class": "SGLT2i",
                            "subgroup": "SGLT2i",
                        }
                    ],
                },
            }
        ],
        _runtime(gout_status=_fact("present", True)),
    )

    assert len(options) == 1
    assert [item["name"] for item in options[0]["medicines"]["D"]] == ["Furosemide"]
    assert "THIAZIDE_LIKE_DIURETIC" in profile["blocked_targets"]


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
