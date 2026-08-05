"""Safety filtering for the trace-derived final medication regimen."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.medication_regimen_contracts import (
    MedicationRegimenPlan,
    RegimenComponent,
    RegimenKeyword,
)
from cdss.domain.medication_safety import evaluate_target, target_for_medicine
from cdss.domain.medication_safety_catalog import has_safety_data
from cdss.domain.medication_safety_regimen_helpers import (
    component_matches_removal,
    raw_matches_removal,
    relative_findings_for_medicine,
)


def filter_medication_regimen_plan(
    plan: MedicationRegimenPlan,
    runtime: Mapping[str, Any],
) -> MedicationRegimenPlan:
    """Remove unsafe medicines from the final regimen and its display catalog."""

    if not has_safety_data(runtime):
        return plan

    def safe(raw: Mapping[str, Any]) -> bool:
        result = evaluate_target(target_for_medicine(raw), runtime, medicine=raw)
        return result["status"] not in {"ABSOLUTE", "INSUFFICIENT_DATA"}

    def display_item(raw: Mapping[str, Any]) -> dict[str, Any]:
        """Keep relative options visible while carrying their warning to the UI."""

        item = dict(raw)
        result = evaluate_target(target_for_medicine(raw), runtime, medicine=raw)
        if result["status"] != "RELATIVE":
            return item
        relative_findings = relative_findings_for_medicine(raw, result["findings"], runtime)
        if not relative_findings:
            return item
        item["safety_status"] = "RELATIVE"
        item["safety_findings"] = relative_findings
        item["requires_override_reason"] = True
        return item

    final_removals = [
        component
        for step in plan.steps
        if step.keyword is RegimenKeyword.REMOVE
        for component in step.components
    ]

    def raw_is_removed(raw: Mapping[str, Any]) -> bool:
        return any(raw_matches_removal(raw, removed) for removed in final_removals)

    filtered_catalog = [
        display_item(raw)
        for raw in plan.catalog
        if isinstance(raw, Mapping) and safe(raw) and not raw_is_removed(raw)
    ]
    filtered_catalog_by_class = {
        code: [
            display_item(raw)
            for raw in items
            if isinstance(raw, Mapping) and safe(raw) and not raw_is_removed(raw)
        ]
        for code, items in plan.catalog_by_class.items()
    }

    def component_is_removed(component: object) -> bool:
        if not isinstance(component, RegimenComponent):
            return False
        return any(component_matches_removal(component, removed) for removed in final_removals)

    def component_is_safe(component: object) -> bool:
        if component_is_removed(component):
            return False
        if isinstance(component, RegimenComponent):
            raw_component: Mapping[str, Any] = component.model_dump()
        elif isinstance(component, Mapping):
            raw_component = component
        else:
            return True
        if raw_component.get("selector_kind") != "medicine":
            code = raw_component.get("code")
            if not isinstance(code, str):
                return True
            has_subgroup_removal = any(
                removed.selector_kind == "class"
                and removed.code == code
                and removed.subgroup is not None
                for removed in final_removals
            )
            if code == "D" and not has_subgroup_removal:
                # Preserve the legacy behavior when an older caller supplies
                # only a class-level safety finding without the final T6
                # subgroup removal step.
                return evaluate_target("THIAZIDE_LIKE_DIURETIC", runtime)["status"] not in {
                    "ABSOLUTE",
                    "INSUFFICIENT_DATA",
                }
            candidates = filtered_catalog_by_class.get(code, [])
            if not candidates and code in plan.catalog_by_class:
                # The class was present in the source regimen, but every
                # catalog medicine for it was removed by safety filtering.
                # Do not leave an empty class in the final regimen contract.
                return False
            if not candidates:
                candidates = [
                    raw
                    for raw in plan.catalog
                    if isinstance(raw, Mapping) and raw.get("drug_class") == code
                ]
            return not candidates or any(safe(raw) for raw in candidates)
        medicine_id = raw_component.get("medicine_id")
        name = str(raw_component.get("name") or "").casefold()
        matched = next(
            (
                raw
                for raw in plan.catalog
                if isinstance(raw, Mapping)
                and (
                    (isinstance(medicine_id, str) and raw.get("drug_id") == medicine_id)
                    or (name and str(raw.get("name") or "").casefold() == name)
                )
            ),
            None,
        )
        return matched is None or (not raw_is_removed(matched) and safe(matched))

    effective = plan.effective_regimen
    safe_base_options = [
        option
        for option in effective.base_options
        if option.components
        and all(component_is_safe(component) for component in option.components)
    ]
    safe_additions = [
        component for component in effective.additions if component_is_safe(component)
    ]
    status = effective.status
    if safe_base_options and len(safe_base_options) <= 1:
        status = "complete"
    elif len(safe_base_options) > 1:
        status = "choice_required"
    filtered_effective = effective.model_copy(
        update={
            "base_options": safe_base_options,
            "additions": safe_additions,
            "status": status,
        }
    )
    filtered_steps = [
        step.model_copy(
            update={
                "components": [
                    component
                    for component in step.components
                    if step.keyword is RegimenKeyword.REMOVE or component_is_safe(component)
                ],
                "alternatives": [
                    alternative
                    for alternative in step.alternatives
                    if alternative.components
                    and (
                        step.keyword is RegimenKeyword.REMOVE
                        or all(component_is_safe(component) for component in alternative.components)
                    )
                ],
            }
        )
        for step in plan.steps
    ]
    referenced_classes = {
        component.code
        for step in filtered_steps
        for component in [
            *step.components,
            *(item for option in step.alternatives for item in option.components),
        ]
        if step.keyword is not RegimenKeyword.REMOVE
        and component.selector_kind == "class"
        and component.code
    }
    referenced_classes.update(
        component.code
        for option in filtered_effective.base_options
        for component in option.components
        if component.selector_kind == "class" and component.code
    )
    referenced_classes.update(
        component.code
        for component in filtered_effective.additions
        if component.selector_kind == "class" and component.code
    )
    filtered_catalog_by_class = {
        code: items
        for code, items in filtered_catalog_by_class.items()
        if code in referenced_classes and items
    }
    return plan.model_copy(
        update={
            "steps": filtered_steps,
            "effective_regimen": filtered_effective,
            "catalog": filtered_catalog,
            "catalog_by_class": filtered_catalog_by_class,
        }
    )


__all__ = ["filter_medication_regimen_plan"]
