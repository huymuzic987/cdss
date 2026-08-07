"""Extraction helpers for medication regimen components."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard

from cdss.domain.decision_tree.medication_regimen_contracts import (
    DEFAULT_REGIMEN_DOSE_STRATEGY,
    RegimenAlternative,
    RegimenComponent,
)
from cdss.domain.decision_tree.medication_regimen_subgroups import catalog_group_matches
from cdss.domain.decision_tree.medicine_catalog import Medicine

_CLASS_TOKEN_PATTERN = re.compile(r"(?<![A-Z0-9])([ABCD])(?![A-Z0-9])")
_CANONICAL_CLASS_ALIASES = {
    "SGLT2_INHIBITOR": "SGLT2i",
    "SGLT2 INHIBITOR": "SGLT2i",
    "GLP1_RECEPTOR_AGONIST": "GLP1RA",
    "GLP1 RECEPTOR AGONIST": "GLP1RA",
    "GLP-1RA": "GLP1RA",
    "GLP-1 RA": "GLP1RA",
}


def structured_update(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    update = payload.get("regimen_update")
    return update if isinstance(update, Mapping) else None


def components_from_update(
    update: Mapping[str, Any],
) -> tuple[list[RegimenComponent], list[RegimenAlternative]]:
    components = _parse_components(update.get("components"), update)
    alternatives: list[RegimenAlternative] = []
    raw_alternatives = update.get("alternatives")
    if _sequence(raw_alternatives):
        for raw in raw_alternatives:
            if isinstance(raw, Mapping):
                parsed = _parse_components(raw.get("components"), raw)
                if parsed:
                    alternatives.append(RegimenAlternative(components=parsed))
    return components, alternatives


def components_from_context(
    patch: Mapping[str, Any] | None,
) -> tuple[list[RegimenComponent], list[RegimenAlternative]]:
    if not isinstance(patch, Mapping):
        return [], []
    preferences = patch.get("treatment_preferences")
    if not isinstance(preferences, Mapping):
        return [], []
    dose_strategy = _string(preferences.get("dose_strategy")) or DEFAULT_REGIMEN_DOSE_STRATEGY
    alternatives = [
        RegimenAlternative(
            components=[
                class_component(code, dose_strategy)
                for code in raw
                if isinstance(code, str) and code.strip()
            ]
        )
        for raw in _lists(preferences.get("combination_options"))
    ]
    escalations = preferences.get("escalation_options")
    if _sequence(escalations):
        for raw in escalations:
            if not isinstance(raw, Mapping):
                continue
            classes = raw.get("classes")
            if not _sequence(classes):
                continue
            components = [
                class_component(code, _string(raw.get("dose_strategy")) or dose_strategy)
                for code in classes
                if isinstance(code, str) and code.strip()
            ]
            if components:
                alternatives.append(RegimenAlternative(components=components))
    additional = preferences.get("additional_drug_classes")
    components = (
        [
            class_component(
                code,
                _string(preferences.get("additional_dose_strategy"))
                or DEFAULT_REGIMEN_DOSE_STRATEGY,
            )
            for code in additional
            if isinstance(code, str) and code.strip()
        ]
        if _sequence(additional)
        else []
    )
    return components, [option for option in alternatives if option.components]


def components_from_text(text: str, catalog: list[Medicine]) -> list[RegimenComponent]:
    lowered = text.casefold()
    components: list[RegimenComponent] = []
    seen: set[str] = set()
    named_medicines: list[Medicine] = []
    for medicine in catalog:
        if medicine.name.casefold() in lowered and not _negated(medicine.name, lowered):
            key = f"medicine:{medicine.drug_id}"
            if key not in seen:
                seen.add(key)
                named_medicines.append(medicine)
                components.append(
                    RegimenComponent(
                        selector_kind="medicine",
                        medicine_id=medicine.drug_id,
                        name=medicine.name,
                    )
                )
    group_matches = (
        catalog_group_matches(text, catalog)
        if catalog
        else [(code, None) for code in _CLASS_TOKEN_PATTERN.findall(text.upper())]
    )
    for code, subgroup in group_matches:
        if any(_medicine_in_group(medicine, code) for medicine in named_medicines):
            continue
        key = f"class:{code}:{subgroup or ''}"
        if key not in seen:
            seen.add(key)
            components.append(class_component(code, DEFAULT_REGIMEN_DOSE_STRATEGY, subgroup))
    return components


def medicine_json(medicine: Medicine) -> dict[str, Any]:
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
        "snomed_code": medicine.snomed_code,
    }


def class_component(
    code: str,
    dose_strategy: str,
    subgroup: str | None = None,
) -> RegimenComponent:
    normalized_code = _CANONICAL_CLASS_ALIASES.get(code.strip().upper(), code.strip())
    return RegimenComponent(
        selector_kind="class",
        code=normalized_code,
        subgroup=subgroup,
        dose_strategy=dose_strategy or DEFAULT_REGIMEN_DOSE_STRATEGY,
    )


def _medicine_in_group(medicine: Medicine, group: str) -> bool:
    if group == "MRA":
        return medicine.drug_class == "MRA" or bool(
            medicine.subgroup and "MRA" in medicine.subgroup.upper()
        )
    return bool(medicine.drug_class and medicine.drug_class.casefold() == group.casefold())


def _parse_components(value: object, defaults: Mapping[str, Any]) -> list[RegimenComponent]:
    if not _sequence(value):
        return []
    output: list[RegimenComponent] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        code = _string(raw.get("code"))
        medicine_id = _string(raw.get("medicine_id"))
        name = _string(raw.get("name"))
        subgroup = _string(raw.get("subgroup"))
        kind = raw.get("selector_kind")
        if kind not in {"class", "medicine"}:
            kind = "class" if code else "medicine"
        if (kind == "class" and not code) or (kind == "medicine" and not (medicine_id or name)):
            continue
        output.append(
            RegimenComponent(
                selector_kind=kind,
                code=code,
                medicine_id=medicine_id,
                name=name,
                subgroup=subgroup,
                dose_strategy=_string(raw.get("dose_strategy"))
                or _string(defaults.get("dose_strategy"))
                or DEFAULT_REGIMEN_DOSE_STRATEGY,
                dose=_string(raw.get("dose")),
                route=_string(raw.get("route")),
                frequency=_string(raw.get("frequency")),
                duration=_string(raw.get("duration")),
            )
        )
    return output


def _lists(value: object) -> list[list[Any]]:
    return [list(item) for item in value if _sequence(item)] if _sequence(value) else []


def _sequence(value: object) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _negated(name: str, text: str) -> bool:
    position = text.find(name.casefold())
    prefix = text[max(0, position - 72) : position] if position >= 0 else ""
    return any(
        marker in prefix
        for marker in ("do not", "avoid", "contraind", "not use", "stop", "discontinue")
    )


def _string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
