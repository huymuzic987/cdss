from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import cast

from cdss.api.routes.evaluation_presentation import enrich_inferred_medications
from cdss.domain.decision_tree import (
    ExecutedAction,
    NodeType,
    TraceEvent,
    TraversalResult,
    TreeGraphRepository,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine


class _MedicineRepository:
    def __init__(self, medicines: Sequence[Medicine]) -> None:
        self._medicines = medicines

    def get_by_id(self, drug_id: str) -> Medicine | None:
        return next((medicine for medicine in self._medicines if medicine.drug_id == drug_id), None)

    def list_by_class(self, drug_class: str) -> Sequence[Medicine]:
        return [medicine for medicine in self._medicines if medicine.drug_class == drug_class]

    def list_all(self) -> Sequence[Medicine]:
        return self._medicines


def test_malformed_medicine_class_is_ignored_when_enriching_actions() -> None:
    action = ExecutedAction(
        tree_key="example",
        node_key="malformed-medicine",
        node_type=NodeType.END,
        text_en="Recommendation",
        text_vi="Khuyến nghị",
        payload={
            "medicines": [
                {"name": "Malformed", "drug_class": []},
                {"name": "Losartan", "drug_class": "A"},
            ]
        },
    )
    result = cast(
        TraversalResult,
        SimpleNamespace(context={}, trace=[], actions=[]),
    )
    repository = _MedicineRepository(
        [
            Medicine(
                drug_id="DRUG0001",
                name="Losartan",
                drug_class="A",
                subgroup="ARB",
                route="Thuốc Uống",
                dose_low="25 mg",
                dose_usual="50 mg",
                dose_max="100 mg",
                source="test",
                link=None,
                available=True,
            )
        ]
    )

    enriched = enrich_inferred_medications(
        [action], result, cast(TreeGraphRepository, None), repository
    )

    assert enriched[0].payload["medicine_catalog_by_class"] == {
        "A": [
            {
                "drug_id": "DRUG0001",
                "name": "Losartan",
                "drug_class": "A",
                "subgroup": "ARB",
                "route": "Thuốc Uống",
                "dose_low": "25 mg",
                "dose_usual": "50 mg",
                "dose_max": "100 mg",
                "source": "test",
                "link": None,
                "available": True,
            }
        ]
    }


def test_every_positive_traversed_drug_and_regimen_reaches_terminal_presentation() -> None:
    losartan = Medicine(
        drug_id="DRUG0001",
        name="Losartan",
        drug_class="A",
        subgroup="ARB",
        route="Thuá»‘c Uá»‘ng",
        dose_low="25 mg",
        dose_usual="50 mg",
        dose_max="100 mg",
        source="test",
        link=None,
        available=True,
    )
    amlodipine = Medicine(
        drug_id="DRUG0002",
        name="Amlodipine",
        drug_class="C",
        subgroup="CCB",
        route="Thuá»‘c Uá»‘ng",
        dose_low="2.5 mg",
        dose_usual="5 mg",
        dose_max="10 mg",
        source="test",
        link=None,
        available=True,
    )
    spironolactone = Medicine(
        drug_id="DRUG0003",
        name="Spironolactone",
        drug_class="MRA",
        subgroup="MRA",
        route="Thuá»‘c Uá»‘ng",
        dose_low="12.5 mg",
        dose_usual="25 mg",
        dose_max="50 mg",
        source="test",
        link=None,
        available=True,
    )
    hydrochlorothiazide = Medicine(
        drug_id="DRUG0004",
        name="Hydrochlorothiazide",
        drug_class="D",
        subgroup="Thiazide",
        route="Thuá»‘c Uá»‘ng",
        dose_low="12.5 mg",
        dose_usual="25 mg",
        dose_max="50 mg",
        source="test",
        link=None,
        available=True,
    )
    catalog = [losartan, amlodipine, spironolactone, hydrochlorothiazide]
    repository = _MedicineRepository(catalog)
    medicine_json = {
        "drug_id": losartan.drug_id,
        "name": losartan.name,
        "drug_class": losartan.drug_class,
        "dose_low": losartan.dose_low,
        "available": True,
    }
    earlier_action = ExecutedAction(
        tree_key="regimen",
        node_key="choose-combination",
        node_type=NodeType.ACTION,
        text_en="Choose regimen",
        text_vi="Choose regimen",
        payload={
            "medicines": [medicine_json],
            "medicine_options": [
                {
                    "classes": ["A", "C"],
                    "dose_strategy": "LOW_DOSE",
                    "medicines": {
                        "A": [medicine_json],
                        "C": [
                            {
                                "drug_id": amlodipine.drug_id,
                                "name": amlodipine.name,
                                "drug_class": amlodipine.drug_class,
                                "dose_low": amlodipine.dose_low,
                                "available": True,
                            }
                        ],
                    },
                }
            ],
        },
    )
    terminal = ExecutedAction(
        tree_key="regimen",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Use the completed regimen",
        text_vi="Use the completed regimen",
        payload={"medicines": [medicine_json]},
    )
    nodes = {
        "choose-combination": SimpleNamespace(
            text_en="Choose Losartan with Amlodipine",
            text_vi="",
        ),
        "add-mra": SimpleNamespace(
            text_en="Add Spironolactone to the regimen",
            text_vi="",
        ),
        "safety": SimpleNamespace(
            text_en="Avoid Hydrochlorothiazide because it is contraindicated",
            text_vi="",
        ),
        "terminal": SimpleNamespace(text_en=terminal.text_en, text_vi=terminal.text_vi),
    }
    tree_repository = SimpleNamespace(
        get_tree=lambda _tree_key: SimpleNamespace(nodes_by_key=nodes)
    )
    trace = [
        SimpleNamespace(event=TraceEvent.NODE_ENTERED, tree_key="regimen", node_key=node_key)
        for node_key in nodes
    ]
    result = cast(
        TraversalResult,
        SimpleNamespace(context={}, trace=trace, actions=[earlier_action, terminal]),
    )

    enriched = enrich_inferred_medications(
        [terminal],
        result,
        cast(TreeGraphRepository, tree_repository),
        repository,
    )

    payload = enriched[0].payload
    assert [medicine["name"] for medicine in payload["medicines"]] == ["Spironolactone"]
    assert "Hydrochlorothiazide" not in {medicine["name"] for medicine in payload["medicines"]}
    assert payload["medicine_options"] == earlier_action.payload["medicine_options"]
    assert set(payload["medicine_catalog_by_class"]) == {"A", "C"}


def test_maintain_inference_does_not_rebuild_context_as_a_new_regimen() -> None:
    terminal = ExecutedAction(
        tree_key="drug-combination",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Maintain regimen",
        text_vi="Maintain regimen",
        payload={},
    )
    maintain_key = "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_ADJUSTMENT"
    nodes = {
        maintain_key: SimpleNamespace(
            node_type=NodeType.INFERENCE,
            text_en="Maintain regimen",
            text_vi="Maintain regimen",
            action_payload=None,
            context_patch=None,
        )
    }
    tree_repository = SimpleNamespace(
        get_tree=lambda _tree_key: SimpleNamespace(nodes_by_key=nodes)
    )
    result = cast(
        TraversalResult,
        SimpleNamespace(
            context={"treatment_preferences": {"combination_options": [["A", "C"]]}},
            actions=[terminal],
            trace=[
                SimpleNamespace(
                    step=1,
                    event=TraceEvent.NODE_ENTERED,
                    tree_key="drug-combination",
                    node_key=maintain_key,
                    node_type=NodeType.INFERENCE,
                )
            ],
        ),
    )

    enriched = enrich_inferred_medications(
        [terminal],
        result,
        cast(TreeGraphRepository, tree_repository),
        _MedicineRepository([]),
    )

    assert "medicine_options" not in enriched[0].payload
    regimen_plan = enriched[0].payload["regimen_plan"]
    assert [step["keyword"] for step in regimen_plan["steps"]] == ["MAINTAIN"]
    assert regimen_plan["steps"][0]["components"] == []
    assert regimen_plan["effective_regimen"]["additions"] == []


def test_hfmref_action_type_resolves_sglt2i_and_aldosterone_antagonists() -> None:
    def medicine(
        drug_id: str,
        name: str,
        drug_class: str,
        subgroup: str,
        dose: str,
    ) -> Medicine:
        return Medicine(
            drug_id=drug_id,
            name=name,
            drug_class=drug_class,
            subgroup=subgroup,
            route="Thuá»‘c Uá»‘ng",
            dose_low=dose,
            dose_usual=dose,
            dose_max=dose,
            source="test",
            link=None,
            available=True,
        )

    catalog = [
        medicine("DRUG-D", "Hydrochlorothiazide", "D", "Thiazide", "12.5 mg"),
        medicine("DRUG-MRA-1", "Eplerenone", "D", "LT giá»¯ Kali", "25 mg"),
        medicine("DRUG-MRA-2", "Spironolactone", "D", "LT giá»¯ Kali", "12.5 mg"),
        medicine("DRUG-SGLT2-1", "Dapagliflozin", "SGLT2i", "SGLT2i", "5-10 mg"),
        medicine("DRUG-SGLT2-2", "Empagliflozin", "SGLT2i", "SGLT2i", "10 mg"),
    ]
    class_d = [
        {
            "drug_id": item.drug_id,
            "name": item.name,
            "drug_class": item.drug_class,
            "dose_low": item.dose_low,
            "available": item.available,
        }
        for item in catalog
        if item.drug_class == "D"
    ]
    terminal = ExecutedAction(
        tree_key="hypertension-heart-failure",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Continue the established regimen",
        text_vi="Tiáº¿p tá»¥c phÃ¡c Ä‘á»“",
        payload={
            "medicine_options": [
                {
                    "classes": ["A", "D"],
                    "dose_strategy": "LOW_DOSE",
                    "medicines": {"A": [], "D": class_d},
                }
            ]
        },
    )
    nodes = {
        "T10_I_HFMREF_1": SimpleNamespace(
            text_en="Combine D and SGLT2i and Aldosterone antagonist",
            text_vi="Phá»‘i há»£p D vÃ  SGLT2i vÃ  khÃ¡ng Aldosterone",
            action_payload={"action_type": "COMBINE_D_SGLT2I_ALDO"},
        ),
        "terminal": SimpleNamespace(
            text_en=terminal.text_en,
            text_vi=terminal.text_vi,
            action_payload=None,
        ),
    }
    tree_repository = SimpleNamespace(
        get_tree=lambda _tree_key: SimpleNamespace(nodes_by_key=nodes)
    )
    result = cast(
        TraversalResult,
        SimpleNamespace(
            context={},
            actions=[terminal],
            trace=[
                SimpleNamespace(
                    event=TraceEvent.NODE_ENTERED,
                    tree_key="hypertension-heart-failure",
                    node_key=node_key,
                )
                for node_key in nodes
            ],
        ),
    )

    enriched = enrich_inferred_medications(
        [terminal],
        result,
        cast(TreeGraphRepository, tree_repository),
        _MedicineRepository(catalog),
    )

    assert {item["name"] for item in enriched[0].payload["medicines"]} == {
        "Dapagliflozin",
        "Empagliflozin",
    }
    represented = enriched[0].payload["medicine_options"][0]["medicines"]["D"]
    assert {item["name"] for item in represented} == {
        "Hydrochlorothiazide",
        "Eplerenone",
        "Spironolactone",
    }
    regimen_steps = enriched[0].payload["regimen_plan"]["steps"]
    assert [item["code"] for item in regimen_steps[0]["components"]] == [
        "D",
        "SGLT2i",
        "MRA",
    ]
    assert all(item["dose_strategy"] == "LOW_DOSE" for item in regimen_steps[0]["components"])
