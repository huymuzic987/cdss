"""Public traversal-wide medication regimen construction."""

from __future__ import annotations

import re
from typing import Literal

from cdss.domain.decision_tree.contracts import (
    NodeType,
    TraceEvent,
    TraversalResult,
)
from cdss.domain.decision_tree.errors import DecisionTreeError
from cdss.domain.decision_tree.graph import NodeDefinition, TreeGraphRepository
from cdss.domain.decision_tree.medication_regimen_actions import (
    components_from_action_payload,
)
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
from cdss.domain.decision_tree.medication_regimen_values import (
    components_from_context,
    components_from_text,
    components_from_update,
    medicine_json,
    structured_update,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine, MedicineRepository

_KEYWORD_PATTERN = re.compile(r"^T\d+_INFERENCE_([A-Z]+)_")
_TREATMENT_KEYWORDS = frozenset(
    {
        RegimenKeyword.START,
        RegimenKeyword.ADD,
        RegimenKeyword.COMBINE,
        RegimenKeyword.SELECT,
        RegimenKeyword.ADJUST,
        RegimenKeyword.CHANGE,
        RegimenKeyword.ESCALATE,
        RegimenKeyword.REDUCE,
        RegimenKeyword.STOP,
        RegimenKeyword.KEEP,
        RegimenKeyword.MAINTAIN,
        RegimenKeyword.MONITOR,
        RegimenKeyword.AVOID,
        RegimenKeyword.RESTORE,
    }
)
_COMPONENT_OPTIONAL_KEYWORDS = frozenset(
    {RegimenKeyword.ADJUST, RegimenKeyword.KEEP, RegimenKeyword.MONITOR}
)


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
        keyword = _keyword_for_node(node, entry.node_key)
        if keyword is None:
            continue
        step = _step_for_node(
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
                or (
                    component.name
                    and item.name.casefold() in component.name.casefold()
                )
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
                or (
                    code == "MRA"
                    and item.subgroup is not None
                    and "MRA" in item.subgroup.upper()
                )
            ]
            for code in sorted(selected_classes)
        },
    )


def _keyword_for_node(node: NodeDefinition, node_key: str) -> RegimenKeyword | None:
    match = _KEYWORD_PATTERN.match(node_key)
    if match:
        try:
            return RegimenKeyword(match.group(1))
        except ValueError:
            pass
    text = node.text_en.strip().casefold()
    for prefix, keyword in (
        ("start", RegimenKeyword.START),
        ("drug therapy: start", RegimenKeyword.START),
        ("add", RegimenKeyword.ADD),
        ("combine", RegimenKeyword.COMBINE),
        ("select", RegimenKeyword.SELECT),
        ("adjust", RegimenKeyword.ADJUST),
        ("change", RegimenKeyword.CHANGE),
        ("increase", RegimenKeyword.ESCALATE),
        ("reduce", RegimenKeyword.REDUCE),
        ("stop", RegimenKeyword.STOP),
        ("keep", RegimenKeyword.KEEP),
        ("maintain", RegimenKeyword.MAINTAIN),
        ("monitor", RegimenKeyword.MONITOR),
        ("avoid", RegimenKeyword.AVOID),
    ):
        if text.startswith(prefix):
            return keyword
    return None


def _step_for_node(
    node: NodeDefinition,
    *,
    node_key: str,
    keyword: RegimenKeyword,
    trace_step: int,
    tree_key: str,
    catalog: list[Medicine],
) -> RegimenUpdateStep | None:
    update = structured_update(getattr(node, "action_payload", None))
    if keyword is RegimenKeyword.MAINTAIN:
        return RegimenUpdateStep(
            id=f"{tree_key}:{node_key}:{trace_step}",
            trace_step=trace_step,
            tree_key=tree_key,
            node_key=node_key,
            keyword=keyword,
            text_en=node.text_en,
            text_vi=node.text_vi,
            source="structured" if update is not None else "legacy",
        )
    if update is not None:
        components, alternatives = components_from_update(update)
        source: Literal["structured", "context", "legacy"] = "structured"
    else:
        components, alternatives = components_from_context(getattr(node, "context_patch", None))
        source = "context"
    if not components and not alternatives:
        components, alternatives = components_from_action_payload(
            getattr(node, "action_payload", None)
        )
        source = "legacy"
    if not components and not alternatives:
        components = components_from_text(node.text_en, catalog)
        source = "legacy"
    if keyword is RegimenKeyword.SELECT and components and not alternatives:
        alternatives = [
            RegimenAlternative(components=[component]) for component in components
        ]
        components = []
    if (
        not components
        and not alternatives
        and keyword not in _COMPONENT_OPTIONAL_KEYWORDS
    ) or keyword not in _TREATMENT_KEYWORDS:
        return None
    return RegimenUpdateStep(
        id=f"{tree_key}:{node_key}:{trace_step}",
        trace_step=trace_step,
        tree_key=tree_key,
        node_key=node_key,
        keyword=keyword,
        text_en=node.text_en,
        text_vi=node.text_vi,
        source=source,
        components=components,
        alternatives=alternatives,
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
