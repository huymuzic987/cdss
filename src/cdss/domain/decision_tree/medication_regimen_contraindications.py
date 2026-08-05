"""Final subgroup-aware contraindication operation for medication regimens."""

from __future__ import annotations

from collections.abc import Mapping

from cdss.domain.decision_tree.contracts import TraceEvent, TraversalResult
from cdss.domain.decision_tree.medication_regimen_contracts import (
    RegimenComponent,
    RegimenKeyword,
    RegimenUpdateStep,
)

_NODE_KEY = "T6_INFERENCE_DETERMINE_CONTRAINDICATIONS"
_CLASS_CODES = {
    "ACE_INHIBITOR": "A",
    "ARB": "A",
    "DIRECT_RENIN_INHIBITOR": "A",
    "DIRECT_RENIN_INHIBITOR_OR_VASODILATOR": "A",
    "BETA_BLOCKER": "B",
    "DIHYDROPYRIDINE_CCB": "C",
    "NON_DIHYDROPYRIDINE_CCB": "C",
    "THIAZIDE_LIKE_DIURETIC": "D",
    "MRA": "MRA",
}
_REMOVAL_SEVERITY = "ABSOLUTE"


def contraindication_removal_step(
    result: TraversalResult,
    steps: list[RegimenUpdateStep],
) -> RegimenUpdateStep | None:
    if not any(
        entry.event is TraceEvent.NODE_ENTERED and entry.node_key == _NODE_KEY
        for entry in result.trace
    ):
        return None
    runtime = getattr(result, "input_snapshot", {})
    findings = runtime.get("contraindication_findings", [])
    has_detailed_findings = isinstance(findings, (list, tuple))
    components: list[RegimenComponent] = []
    warnings: list[str] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    if isinstance(findings, (list, tuple)):
        for item in findings:
            if not isinstance(item, Mapping) or item.get("severity") != _REMOVAL_SEVERITY:
                continue
            target = item.get("target")
            code = _CLASS_CODES.get(target.upper()) if isinstance(target, str) else None
            if code is None:
                continue
            subgroup = _text(item.get("drug_group"))
            drug_name = _text(item.get("drugs"))
            identity = (code, subgroup, drug_name)
            if identity in seen:
                continue
            seen.add(identity)
            components.append(
                RegimenComponent(
                    selector_kind="medicine" if drug_name else "class",
                    code=None if drug_name else code,
                    name=drug_name,
                    subgroup=None if drug_name else subgroup,
                )
            )
            warnings.append(f"CONTRAINDICATION:{target}:{_component_label(components[-1])}")
    # The legacy class list has no severity information. Only use it when a
    # caller did not provide the detailed findings; otherwise a RELATIVE
    # finding could accidentally be converted into a destructive REMOVE step.
    if not components and not has_detailed_findings:
        targets = runtime.get("contraindicated_drug_classes", [])
        if isinstance(targets, (list, tuple)):
            for target in targets:
                code = _CLASS_CODES.get(target.upper()) if isinstance(target, str) else None
                if code and (code, None, None) not in seen:
                    seen.add((code, None, None))
                    components.append(RegimenComponent(selector_kind="class", code=code))
                    warnings.append(f"CONTRAINDICATION:{target}:{_component_label(components[-1])}")
    if not components:
        return None
    last_trace_step = max((getattr(entry, "step", 0) for entry in result.trace), default=0)
    details_en = ", ".join(_component_label(component) for component in components)
    details_vi = details_en
    return RegimenUpdateStep(
        id=f"drug-combination:{_NODE_KEY}:final-removal",
        trace_step=max(last_trace_step, max((step.trace_step for step in steps), default=0)) + 1,
        tree_key="drug-combination",
        node_key=_NODE_KEY,
        keyword=RegimenKeyword.REMOVE,
        text_en=(
            "Remove matched contraindicated drug groups from the final regimen: "
            f"{details_en}"
        ),
        text_vi=(
            "Loại bỏ các nhóm thuốc chống chỉ định khỏi phác đồ cuối cùng: "
            f"{details_vi}"
        ),
        source="context",
        components=components,
        warnings=warnings,
    )


def _text(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _component_label(component: RegimenComponent) -> str:
    if component.selector_kind == "medicine":
        return component.name or component.medicine_id or "medicine"
    if component.subgroup:
        return f"{component.code} ({component.subgroup})"
    return component.code or "drug group"
