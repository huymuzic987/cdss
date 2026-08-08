from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from cdss.domain.medication_safety.medication_safety import (
    evaluate_medication_safety,
)
from cdss.domain.medication_safety.medication_safety_action_catalog import ACTION_SELECTORS
from cdss.domain.medication_safety.medication_safety_catalog import (
    has_safety_data,
    medicine_json,
)
from cdss.domain.medication_safety.medication_safety_inputs import (
    target_for_medicine,
)
from cdss.domain.medication_safety.medication_safety_interactions import (
    dual_ras_blockade_finding,
)
from cdss.domain.medication_safety.medication_safety_rules import evaluate_target

type JsonObject = dict[str, Any]

if TYPE_CHECKING:
    from cdss.domain.decision_tree.medicine_catalog import Medicine, MedicineRepository

_SELECTOR_TARGETS = {
    "ACE_INHIBITOR": "ACE_INHIBITOR",
    "ARB": "ARB",
    "DIRECT_RENIN_INHIBITOR": "DIRECT_RENIN_INHIBITOR",
    "DHP_CCB": "DIHYDROPYRIDINE_CCB",
    "DIHYDROPYRIDINE_CCB": "DIHYDROPYRIDINE_CCB",
    "NON_DHP_CCB": "NON_DIHYDROPYRIDINE_CCB",
    "NON_DIHYDROPYRIDINE_CCB": "NON_DIHYDROPYRIDINE_CCB",
    "BETA_BLOCKER": "BETA_BLOCKER",
    "THIAZIDE_LIKE_DIURETIC": "THIAZIDE_LIKE_DIURETIC",
}


def _catalog_selector(selector: str, repository: MedicineRepository) -> list[Medicine]:
    if selector in {"A", "B", "C", "D"}:
        return list(repository.list_by_class(selector))
    catalog = list(repository.list_all())
    if selector == "MRA":
        return [item for item in catalog if target_for_medicine(item, selector) == "MRA"]
    if selector == "SGLT2i":
        return [
            item for item in catalog if target_for_medicine(item, selector) == "SGLT2_INHIBITOR"
        ]
    target = _SELECTOR_TARGETS.get(selector)
    if target is not None:
        return [item for item in catalog if target_for_medicine(item) == target]
    return [item for item in catalog if item.name.casefold() == selector.casefold()]


def _filter_option(
    option: Mapping[str, Any], runtime: Mapping[str, Any], context: str
) -> tuple[JsonObject | None, list[JsonObject]]:
    classes = [item for item in option.get("classes", []) if isinstance(item, str)]
    raw_map = option.get("medicines")
    if not isinstance(raw_map, Mapping):
        return None, []
    safe_map: JsonObject = {}
    findings: list[JsonObject] = []
    requires_override_reason = False
    for selector in classes:
        if selector == "D":
            class_safety = evaluate_target(
                "THIAZIDE_LIKE_DIURETIC", runtime, clinical_context=context
            )
            # D contains multiple subgroups. Keep the D option when at least
            # one subgroup (for example loop or potassium-sparing diuretics)
            # remains eligible; the medicine loop below removes only the
            # contraindicated subgroup medicines.
            findings.extend(class_safety["findings"])
        raw_items = raw_map.get(selector)
        if not isinstance(raw_items, list):
            return None, findings
        safe_items: list[JsonObject] = []
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                continue
            target = target_for_medicine(raw, selector)
            safety = evaluate_target(target, runtime, medicine=raw, clinical_context=context)
            findings.extend(safety["findings"])
            if safety["status"] not in {"ABSOLUTE", "INSUFFICIENT_DATA"}:
                item = {
                    **deepcopy(dict(raw)),
                    "safety_status": safety["status"],
                    "safety_findings": deepcopy(safety["findings"]),
                }
                if safety["status"] == "RELATIVE":
                    item["requires_override_reason"] = True
                    requires_override_reason = True
                safe_items.append(item)
        if not safe_items:
            return None, findings
        safe_map[selector] = safe_items
    selector_targets = {target_for_medicine({}, selector) for selector in classes}
    if {"ACE_INHIBITOR", "ARB"}.issubset(selector_targets):
        findings.append(dual_ras_blockade_finding())
        return None, findings
    filtered = {
        **deepcopy(dict(option)),
        "medicines": safe_map,
        "safety_warnings": findings,
    }
    if requires_override_reason:
        filtered["requires_override_reason"] = True
    return filtered, findings


def filter_medicine_options(
    options: Sequence[Mapping[str, Any]],
    runtime: Mapping[str, Any],
    *,
    clinical_context: str = "chronic_hypertension",
) -> tuple[list[JsonObject], JsonObject]:
    if not has_safety_data(runtime):
        return [deepcopy(dict(option)) for option in options], evaluate_medication_safety(runtime)
    safe: list[JsonObject] = []
    findings: list[JsonObject] = []
    for option in options:
        filtered, option_findings = _filter_option(option, runtime, clinical_context)
        findings.extend(option_findings)
        if filtered is not None:
            safe.append(filtered)
    profile = evaluate_medication_safety(runtime, medicines=[])
    profile["findings"] = findings
    profile["blocked_targets"] = sorted(
        {str(item["target"]) for item in findings if item["severity"] == "ABSOLUTE"}
    )
    profile["review_targets"] = sorted(
        {
            str(item["target"])
            for item in findings
            if item["severity"] in {"INSUFFICIENT_DATA", "RELATIVE"}
        }
    )
    profile["status"] = (
        "NEEDS_REVIEW"
        if profile["status"] == "NEEDS_REVIEW"
        or any(item["severity"] == "INSUFFICIENT_DATA" for item in findings)
        else "COMPLETE"
    )
    profile["requires_override_reason"] = any(item["severity"] == "RELATIVE" for item in findings)
    return safe, profile


def resolve_safe_regimens(
    payload: Mapping[str, Any],
    context: Mapping[str, Any],
    runtime: Mapping[str, Any],
    repository: MedicineRepository,
) -> tuple[list[JsonObject], JsonObject, bool]:
    explicit = payload.get("candidate_regimens")
    provided_options = payload.get("medicine_options")
    if isinstance(provided_options, list) and all(
        isinstance(item, Mapping) for item in provided_options
    ):
        raw_options = [deepcopy(dict(item)) for item in provided_options]
        clinical_context = str(
            payload.get("clinical_context")
            or ("acute_emergency" if payload.get("target_timing") else "chronic_hypertension")
        )
        safe, profile = filter_medicine_options(
            raw_options, runtime, clinical_context=clinical_context
        )
        return safe, profile, True
    if not isinstance(explicit, list) and isinstance(payload.get("combination_options"), list):
        explicit = payload["combination_options"]
    if not isinstance(explicit, list) and isinstance(payload.get("drug_options"), list):
        explicit = [
            [item["class"]]
            for item in payload["drug_options"]
            if isinstance(item, Mapping) and isinstance(item.get("class"), str)
        ]
    if not isinstance(explicit, list):
        action_type = payload.get("action_type")
        explicit = ACTION_SELECTORS.get(action_type, []) if isinstance(action_type, str) else []
    if explicit:
        raw_options = []
        for regimen in explicit:
            if not isinstance(regimen, list) or not all(isinstance(item, str) for item in regimen):
                continue
            raw_options.append(
                {
                    "classes": list(dict.fromkeys(regimen)),
                    "dose_strategy": payload.get("dose_strategy", "LOW_TO_USUAL_DOSE"),
                    "medicines": {
                        selector: [
                            medicine_json(item)
                            for item in _catalog_selector(selector, repository)
                            if item.available
                        ]
                        for selector in regimen
                    },
                }
            )
    else:
        from cdss.domain.decision_tree.drug_classes import build_medicine_options

        raw_options = build_medicine_options(context, repository) or []
    if not raw_options:
        return [], evaluate_medication_safety(runtime), False
    if not has_safety_data(runtime):
        return (
            [deepcopy(dict(option)) for option in raw_options],
            evaluate_medication_safety(runtime),
            True,
        )
    clinical_context = str(
        payload.get("clinical_context")
        or ("acute_emergency" if payload.get("target_timing") else "chronic_hypertension")
    )
    safe, profile = filter_medicine_options(raw_options, runtime, clinical_context=clinical_context)
    return safe, profile, True
