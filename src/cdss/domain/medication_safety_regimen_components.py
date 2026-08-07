"""Safety filtering for effective regimen components."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.medication_regimen_contracts import (
    EffectiveMedicationRegimen,
    MedicationRegimenPlan,
    RegimenComponent,
    RegimenKeyword,
)
from cdss.domain.medication_safety import evaluate_target, target_for_medicine
from cdss.domain.medication_safety_regimen_helpers import (
    component_matches_removal,
    raw_matches_removal,
)


def filter_effective_regimen(
    plan: MedicationRegimenPlan,
    runtime: Mapping[str, Any],
    final_removals: list[RegimenComponent],
    filtered_catalog_by_class: Mapping[str, list[dict[str, Any]]],
) -> tuple[EffectiveMedicationRegimen, list[RegimenComponent]]:
    """Filter effective options and return components removed by safety."""

    def safe(raw: Mapping[str, Any]) -> bool:
        result = evaluate_target(target_for_medicine(raw), runtime, medicine=raw)
        return result["status"] not in {"ABSOLUTE", "INSUFFICIENT_DATA"}

    def component_is_removed(component: object) -> bool:
        return isinstance(component, RegimenComponent) and any(
            component_matches_removal(component, removed) for removed in final_removals
        )

    def medicine_is_safe(raw_component: Mapping[str, Any]) -> bool:
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
        return matched is None or (
            not any(raw_matches_removal(matched, removed) for removed in final_removals)
            and safe(matched)
        )

    def component_is_safe(component: object) -> bool:
        if component_is_removed(component):
            return False
        if isinstance(component, RegimenComponent):
            raw_component: Mapping[str, Any] = component.model_dump()
        elif isinstance(component, Mapping):
            raw_component = component
        else:
            return True
        if raw_component.get("selector_kind") == "medicine":
            return medicine_is_safe(raw_component)
        code = raw_component.get("code")
        if not code:
            return True
        has_subgroup_removal = any(
            removed.selector_kind == "class"
            and removed.code == code
            and removed.subgroup is not None
            for removed in final_removals
        )
        if code == "D" and not has_subgroup_removal:
            return evaluate_target("THIAZIDE_LIKE_DIURETIC", runtime)["status"] not in {
                "ABSOLUTE",
                "INSUFFICIENT_DATA",
            }
        candidates = filtered_catalog_by_class.get(code, [])
        if not candidates and code in plan.catalog_by_class:
            return False
        if not candidates:
            candidates = [
                raw
                for raw in plan.catalog
                if isinstance(raw, Mapping) and raw.get("drug_class") == code
            ]
        return not candidates or any(safe(raw) for raw in candidates)

    def component_requires_safety_review(component: object) -> bool:
        return (
            isinstance(component, RegimenComponent)
            and component.selector_kind == "class"
            and component.code == "MRA"
            and not component_is_removed(component)
            and evaluate_target("MRA", runtime)["status"] == "INSUFFICIENT_DATA"
        )

    effective = plan.effective_regimen
    safe_base_options = [
        option
        for option in effective.base_options
        if option.components
        and all(
            component_is_safe(component) or component_requires_safety_review(component)
            for component in option.components
        )
    ]
    safe_additions = [
        component
        for component in effective.additions
        if component_is_safe(component) or component_requires_safety_review(component)
    ]
    safety_removed_components: list[RegimenComponent] = []

    def record_safety_removed(component: object) -> None:
        if not isinstance(component, RegimenComponent):
            return
        if component_is_removed(component) or component_is_safe(component):
            return
        if component_requires_safety_review(component) or any(
            component_matches_removal(component, existing) for existing in safety_removed_components
        ):
            return
        safety_removed_components.append(component)

    for step in plan.steps:
        if step.keyword in {RegimenKeyword.REMOVE, RegimenKeyword.AVOID, RegimenKeyword.STOP}:
            continue
        for component in [
            *step.components,
            *(item for alternative in step.alternatives for item in alternative.components),
        ]:
            record_safety_removed(component)
    for component in [
        *(component for option in effective.base_options for component in option.components),
        *effective.additions,
    ]:
        record_safety_removed(component)
    status = effective.status
    if safe_base_options and len(safe_base_options) <= 1:
        status = "complete"
    elif len(safe_base_options) > 1:
        status = "choice_required"
    if status == "complete" and (
        any(
            component_requires_safety_review(component)
            for option in safe_base_options
            for component in option.components
        )
        or any(component_requires_safety_review(component) for component in safe_additions)
    ):
        status = "partial"
    if safety_removed_components and status == "complete":
        status = "partial"
    stopped_components = list(effective.stopped_components)
    for component in safety_removed_components:
        if not any(
            component_matches_removal(component, existing) for existing in stopped_components
        ):
            stopped_components.append(component)
    return (
        effective.model_copy(
            update={
                "base_options": safe_base_options,
                "additions": safe_additions,
                "stopped_components": stopped_components,
                "status": status,
            }
        ),
        safety_removed_components,
    )
