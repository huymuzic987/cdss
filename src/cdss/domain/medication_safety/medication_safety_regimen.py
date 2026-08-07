"""Safety filtering for the trace-derived final medication regimen."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.medication_regimen_contracts import (
    MedicationRegimenPlan,
    RegimenKeyword,
    RegimenUpdateStep,
)
from cdss.domain.medication_safety.medication_safety_catalog import has_safety_data
from cdss.domain.medication_safety.medication_safety_regimen_catalog import filter_regimen_catalog
from cdss.domain.medication_safety.medication_safety_regimen_components import (
    filter_effective_regimen,
)
from cdss.domain.medication_safety.medication_safety_regimen_helpers import (
    component_matches_removal,
)


def filter_medication_regimen_plan(
    plan: MedicationRegimenPlan,
    runtime: Mapping[str, Any],
) -> MedicationRegimenPlan:
    """Remove unsafe medicines from the final regimen and its display catalog."""

    if not has_safety_data(runtime):
        return plan

    final_removals = [
        component
        for step in plan.steps
        if step.keyword is RegimenKeyword.REMOVE
        for component in step.components
    ]
    filtered_catalog, filtered_catalog_by_class = filter_regimen_catalog(
        plan, runtime, final_removals
    )
    filtered_effective, safety_removed_components = filter_effective_regimen(
        plan, runtime, final_removals, filtered_catalog_by_class
    )
    # Keep the collection history intact. The effective regimen above is the
    # actionable, safety-filtered view; the path should show what was
    # collected first and where safety removed it afterward.
    filtered_steps = [step.model_copy(deep=True) for step in plan.steps]
    if safety_removed_components:
        filtered_steps.append(
            RegimenUpdateStep(
                id="medication-safety:REMOVE_UNSAFE_COMPONENTS",
                trace_step=max((step.trace_step for step in plan.steps), default=0) + 1,
                tree_key="medication-safety",
                node_key="MEDICATION_SAFETY_REMOVE_UNSAFE_COMPONENTS",
                keyword=RegimenKeyword.REMOVE,
                text_en=(
                    "Remove the unsafe drug components from the final regimen because "
                    "required medication-safety checks did not pass"
                ),
                text_vi=(
                    "Loại bỏ các thành phần thuốc không an toàn khỏi phác đồ cuối vì "
                    "chưa đạt yêu cầu kiểm tra an toàn thuốc"
                ),
                source="context",
                components=safety_removed_components,
                warnings=[
                    f"SAFETY_REMOVED:{component.code or component.name or 'medicine'}"
                    for component in safety_removed_components
                ],
            )
        )
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
        and not any(
            component_matches_removal(component, removed) for removed in safety_removed_components
        )
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
