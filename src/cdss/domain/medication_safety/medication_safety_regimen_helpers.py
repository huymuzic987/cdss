"""Matching helpers for subgroup-aware regimen removals."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.medication_regimen_contracts import RegimenComponent
from cdss.domain.medication_safety.medication_safety_inputs import target_for_medicine


def raw_matches_removal(raw: Mapping[str, Any], removed: RegimenComponent) -> bool:
    if removed.selector_kind == "medicine":
        if removed.medicine_id and raw.get("drug_id") == removed.medicine_id:
            return True
        name = removed.name
        return bool(
            name and isinstance(raw.get("name"), str) and raw["name"].casefold() == name.casefold()
        )
    drug_class = raw.get("drug_class")
    if removed.code != drug_class and not (
        removed.code == "MRA" and target_for_medicine(raw) == "MRA"
    ):
        return False
    return removed.subgroup is None or subgroup_matches(raw.get("subgroup"), removed.subgroup)


def component_matches_removal(
    component: RegimenComponent,
    removed: RegimenComponent,
) -> bool:
    if removed.selector_kind != component.selector_kind:
        return False
    if removed.selector_kind == "class":
        return removed.code == component.code and (
            removed.subgroup is None or subgroup_matches(component.subgroup, removed.subgroup)
        )
    if removed.medicine_id and component.medicine_id:
        return removed.medicine_id == component.medicine_id
    return bool(
        removed.name and component.name and removed.name.casefold() == component.name.casefold()
    )


def subgroup_matches(value: object, expected: str) -> bool:
    if not isinstance(value, str):
        return False
    actual = value.casefold().strip()
    expected = expected.casefold().strip()
    if actual == expected:
        return True
    aliases = {
        "lợi tiểu thiazide/thiazide-like": {"lt thiazide", "lt thiazide-like"},
        "chẹn beta": {"cb"},
        "ckca nhóm non-dhp": {"ckca non-dhp"},
        "ckca nhóm dhp": {"ckca dhp"},
        "ức chế men chuyển (ace inhibitor)": {"ưcmc"},
        "chẹn thụ thể angiotensin ii (arb)": {"ctta"},
        "đối kháng thụ thể mineralocorticoid (mra)": {"mra (lt giữ kali)"},
    }
    return actual in aliases.get(expected, set())


def relative_findings_for_medicine(
    raw: Mapping[str, Any],
    evaluated: list[Mapping[str, Any]],
    runtime: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return relative findings that apply to this exact catalog medicine."""

    target = target_for_medicine(raw)
    candidates = [
        item
        for item in [*evaluated, *runtime.get("contraindication_findings", [])]
        if isinstance(item, Mapping)
        and item.get("severity") == "RELATIVE"
        and item.get("target") == target
    ]
    findings: list[dict[str, Any]] = []
    seen: set[tuple[object, ...]] = set()
    for item in candidates:
        subgroup = item.get("drug_group")
        if isinstance(subgroup, str) and subgroup.strip():
            if " ".join(str(raw.get("subgroup") or "").casefold().split()) != (
                " ".join(subgroup.casefold().split())
            ):
                continue
        identity = (
            item.get("target"),
            item.get("reason_code"),
            item.get("severity"),
            item.get("drug_group"),
            item.get("drugs"),
        )
        if identity in seen:
            continue
        seen.add(identity)
        findings.append(dict(item))
    return findings
