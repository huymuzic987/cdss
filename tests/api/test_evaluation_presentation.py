from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import cast

from cdss.api.routes.evaluation_presentation import enrich_inferred_medications
from cdss.domain.decision_tree import (
    ExecutedAction,
    NodeType,
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
        SimpleNamespace(context={}, trace=[]),
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
