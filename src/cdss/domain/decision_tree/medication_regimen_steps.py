"""Translate entered decision-tree nodes into regimen update steps."""

from __future__ import annotations

import re
from typing import Literal

from cdss.domain.decision_tree.graph import NodeDefinition
from cdss.domain.decision_tree.medication_regimen_actions import (
    components_from_action_payload,
)
from cdss.domain.decision_tree.medication_regimen_contracts import (
    RegimenAlternative,
    RegimenKeyword,
    RegimenUpdateStep,
)
from cdss.domain.decision_tree.medication_regimen_values import (
    components_from_context,
    components_from_text,
    components_from_update,
    structured_update,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine

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


def keyword_for_node(node: NodeDefinition, node_key: str) -> RegimenKeyword | None:
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


def step_for_node(
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
        alternatives = [RegimenAlternative(components=[component]) for component in components]
        components = []
    if (
        not components and not alternatives and keyword not in _COMPONENT_OPTIONAL_KEYWORDS
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
