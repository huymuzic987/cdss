"""Public traversal-wide medication regimen construction."""

from __future__ import annotations

from cdss.domain.decision_tree.contracts import (
    NodeType,
    TraceEvent,
    TraversalResult,
)
from cdss.domain.decision_tree.errors import DecisionTreeError
from cdss.domain.decision_tree.graph import TreeGraphRepository
from cdss.domain.decision_tree.medication_regimen_contracts import (
    DEFAULT_REGIMEN_DOSE_STRATEGY,
    EffectiveMedicationRegimen,
    MedicationRegimenPlan,
    RegimenAlternative,
    RegimenComponent,
    RegimenKeyword,
    RegimenUpdateStep,
)
from cdss.domain.decision_tree.medication_regimen_state import (
    derive_effective_regimen,
    step_components,
)
from cdss.domain.decision_tree.medication_regimen_steps import keyword_for_node, step_for_node
from cdss.domain.decision_tree.medication_regimen_values import (
    medicine_json,
)
from cdss.domain.decision_tree.medicine_catalog import MedicineRepository


def build_traversed_medication_regimen(
    result: TraversalResult,
    repository: TreeGraphRepository,
    medicine_repository: MedicineRepository,
) -> MedicationRegimenPlan:
    """Build an ordered, reusable medication plan from entered inference nodes."""

    catalog = list(medicine_repository.list_all())
    steps: list[RegimenUpdateStep] = []
    for entry in result.trace:
        if entry.event is not TraceEvent.NODE_ENTERED:
            continue
        try:
            node = repository.get_tree(entry.tree_key).nodes_by_key[entry.node_key]
        except (DecisionTreeError, KeyError, LookupError):
            continue
        node_type = getattr(node, "node_type", getattr(entry, "node_type", None))
        if node_type is not None and node_type is not NodeType.INFERENCE:
            continue
        keyword = keyword_for_node(node, entry.node_key)
        if keyword is None:
            continue
        step = step_for_node(
            node,
            node_key=entry.node_key,
            keyword=keyword,
            trace_step=getattr(entry, "step", len(steps) + 1),
            tree_key=entry.tree_key,
            catalog=catalog,
        )
        if step is not None:
            steps.append(step)

    steps.sort(key=lambda step: (step.keyword is not RegimenKeyword.START, step.trace_step))
    selected_classes = {
        component.code
        for step in steps
        for component in step_components(step)
        if component.selector_kind == "class" and component.code
    }
    selected_medicines = [
        component
        for step in steps
        for component in step_components(step)
        if component.selector_kind == "medicine"
    ]
    for component in selected_medicines:
        matched = next(
            (
                item
                for item in catalog
                if (component.medicine_id and item.drug_id == component.medicine_id)
                or (component.name and item.name.casefold() in component.name.casefold())
            ),
            None,
        )
        if matched and matched.drug_class:
            selected_classes.add(matched.drug_class)
        if matched and matched.subgroup and "MRA" in matched.subgroup.upper():
            selected_classes.add("MRA")
    return MedicationRegimenPlan(
        steps=steps,
        effective_regimen=derive_effective_regimen(sorted(steps, key=lambda step: step.trace_step)),
        catalog=[medicine_json(item) for item in catalog],
        catalog_by_class={
            code: [
                medicine_json(item)
                for item in catalog
                if item.drug_class == code
                or (code == "MRA" and item.subgroup is not None and "MRA" in item.subgroup.upper())
            ]
            for code in sorted(selected_classes)
        },
    )


__all__ = [
    "DEFAULT_REGIMEN_DOSE_STRATEGY",
    "EffectiveMedicationRegimen",
    "MedicationRegimenPlan",
    "RegimenAlternative",
    "RegimenComponent",
    "RegimenKeyword",
    "RegimenUpdateStep",
    "build_traversed_medication_regimen",
]
