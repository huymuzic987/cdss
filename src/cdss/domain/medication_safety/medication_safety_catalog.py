"""Safety filtering for serialized and catalog medication candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from cdss.domain.medication_safety.medication_safety_inputs import (
    target_for_medicine,
)
from cdss.domain.medication_safety.medication_safety_rules import evaluate_target

if TYPE_CHECKING:
    from cdss.domain.decision_tree.medicine_catalog import Medicine

type JsonObject = dict[str, Any]


def filter_catalog_medicines(
    catalog: Sequence[Medicine],
    runtime: Mapping[str, Any],
    *,
    clinical_context: str = "chronic_hypertension",
) -> list[Medicine]:
    """Return catalog items eligible to appear as selectable recommendations."""

    if not _has_safety_data(runtime):
        return list(catalog)
    return [
        item
        for item in catalog
        if evaluate_target(
            target_for_medicine(item),
            runtime,
            medicine=item,
            clinical_context=clinical_context,
        )["status"]
        not in {"ABSOLUTE", "INSUFFICIENT_DATA"}
    ]


def filter_raw_medicines(
    medicines: Sequence[Mapping[str, Any]],
    runtime: Mapping[str, Any],
    *,
    clinical_context: str = "chronic_hypertension",
) -> tuple[list[JsonObject], list[JsonObject]]:
    """Filter serialized medicines while retaining safety annotations."""

    if not _has_safety_data(runtime):
        return [deepcopy(dict(item)) for item in medicines], []
    safe: list[JsonObject] = []
    findings: list[JsonObject] = []
    for raw in medicines:
        result = evaluate_target(
            target_for_medicine(raw),
            runtime,
            medicine=raw,
            clinical_context=clinical_context,
        )
        findings.extend(result["findings"])
        if result["status"] not in {"ABSOLUTE", "INSUFFICIENT_DATA"}:
            safe.append(
                {
                    **deepcopy(dict(raw)),
                    "safety_status": result["status"],
                    "safety_findings": result["findings"],
                }
            )
    return safe, findings


def has_safety_data(runtime: Mapping[str, Any]) -> bool:
    return _has_safety_data(runtime)


def _has_safety_data(runtime: Mapping[str, Any]) -> bool:
    if "clinical_facts" in runtime:
        return True
    return any(
        key in runtime
        for key in {
            "is_pregnant",
            "pregnancy_status",
            "serum_potassium",
            "potassium",
            "eGFR",
            "egfr",
            "active_medication_regimen",
        }
    )


def medicine_json(medicine: Medicine) -> JsonObject:
    return {
        "drug_id": medicine.drug_id,
        "name": medicine.name,
        "drug_class": medicine.drug_class,
        "subgroup": medicine.subgroup,
        "route": medicine.route,
        "dose_low": medicine.dose_low,
        "dose_usual": medicine.dose_usual,
        "dose_max": medicine.dose_max,
        "source": medicine.source,
        "link": medicine.link,
        "available": medicine.available,
    }
