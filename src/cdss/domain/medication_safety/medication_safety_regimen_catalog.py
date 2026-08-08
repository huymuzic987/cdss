"""Safety annotations and visibility rules for regimen catalog entries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.medication_regimen_contracts import (
    MedicationRegimenPlan,
    RegimenComponent,
)
from cdss.domain.medication_safety.medication_safety_inputs import (
    target_for_medicine,
)
from cdss.domain.medication_safety.medication_safety_regimen_helpers import (
    raw_matches_removal,
    relative_findings_for_medicine,
)
from cdss.domain.medication_safety.medication_safety_rules import evaluate_target


def filter_regimen_catalog(
    plan: MedicationRegimenPlan,
    runtime: Mapping[str, Any],
    final_removals: list[RegimenComponent],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Hide unsafe catalog entries and annotate reviewable entries."""

    def catalog_item_visible(raw: Mapping[str, Any]) -> bool:
        result = evaluate_target(target_for_medicine(raw), runtime, medicine=raw)
        if result["status"] == "ABSOLUTE":
            return False
        return result["status"] != "INSUFFICIENT_DATA" or target_for_medicine(raw) == "MRA"

    def display_item(raw: Mapping[str, Any]) -> dict[str, Any]:
        item = dict(raw)
        result = evaluate_target(target_for_medicine(raw), runtime, medicine=raw)
        if result["status"] == "RELATIVE":
            findings = relative_findings_for_medicine(raw, result["findings"], runtime)
            if not findings:
                return item
            item["safety_status"] = "RELATIVE"
            item["safety_findings"] = findings
            item["requires_override_reason"] = True
        elif result["status"] == "INSUFFICIENT_DATA" and target_for_medicine(raw) == "MRA":
            item["safety_status"] = "INSUFFICIENT_DATA"
            item["safety_findings"] = result["findings"]
            item["requires_override_reason"] = False
        return item

    def raw_is_removed(raw: Mapping[str, Any]) -> bool:
        return any(raw_matches_removal(raw, removed) for removed in final_removals)

    filtered_catalog = [
        display_item(raw)
        for raw in plan.catalog
        if isinstance(raw, Mapping) and catalog_item_visible(raw) and not raw_is_removed(raw)
    ]
    filtered_catalog_by_class = {
        code: [
            display_item(raw)
            for raw in items
            if isinstance(raw, Mapping) and catalog_item_visible(raw) and not raw_is_removed(raw)
        ]
        for code, items in plan.catalog_by_class.items()
    }
    return filtered_catalog, filtered_catalog_by_class
