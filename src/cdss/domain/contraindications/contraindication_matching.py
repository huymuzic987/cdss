"""FHIR-code and clinical-fact matching helpers for contraindication rules."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from cdss.domain.medication_safety.medication_safety_contracts import fact_status, fact_value
from cdss.domain.medication_safety.medication_safety_inputs import fact, number

type JsonObject = dict[str, Any]

_ICD_SYSTEM_MARKERS = ("icd-10", "icd10")
_SNOMED_SYSTEM_MARKERS = ("snomed", "sct")
_TARGET_BY_GROUP = {
    "lt thiazide": "THIAZIDE_LIKE_DIURETIC",
    "lt thiazide-like": "THIAZIDE_LIKE_DIURETIC",
    "cb": "BETA_BLOCKER",
    "ưcmc": "ACE_INHIBITOR",
    "ctta": "ARB",
    "ckca non-dhp": "NON_DIHYDROPYRIDINE_CCB",
    "ckca dhp": "DIHYDROPYRIDINE_CCB",
    "mra (lt giữ kali)": "MRA",
    "lt giữ kali": "MRA",
    "ức chế renin trực tiếp": "DIRECT_RENIN_INHIBITOR",
    "thiazide": "THIAZIDE_LIKE_DIURETIC",
    "beta": "BETA_BLOCKER",
    "ace inhibitor": "ACE_INHIBITOR",
    "angiotensin ii": "ARB",
    "arb": "ARB",
    "renin": "DIRECT_RENIN_INHIBITOR",
    "non-dhp": "NON_DIHYDROPYRIDINE_CCB",
    "non-dihydropyridine": "NON_DIHYDROPYRIDINE_CCB",
    "dhp": "DIHYDROPYRIDINE_CCB",
    "dihydropyridine": "DIHYDROPYRIDINE_CCB",
    "mineralocorticoid": "MRA",
}


def target_for_group(value: object) -> str:
    lowered = str(value or "").casefold()
    for marker, target in _TARGET_BY_GROUP.items():
        if marker in lowered:
            return target
    return ""


def condition_codings(bundle: Mapping[str, Any]) -> list[JsonObject]:
    codings: list[JsonObject] = []
    entries = bundle.get("entry")
    if not isinstance(entries, list):
        return codings
    for entry in entries:
        resource = entry.get("resource") if isinstance(entry, Mapping) else None
        if not isinstance(resource, Mapping) or resource.get("resourceType") != "Condition":
            continue
        verification = resource.get("verificationStatus")
        verification_codings = (
            verification.get("coding") if isinstance(verification, Mapping) else None
        )
        if isinstance(verification_codings, list) and any(
            isinstance(item, Mapping) and item.get("code") == "refuted"
            for item in verification_codings
        ):
            continue
        concept = resource.get("code")
        raw_codings = concept.get("coding") if isinstance(concept, Mapping) else None
        if not isinstance(raw_codings, list):
            continue
        for coding in raw_codings:
            if not isinstance(coding, Mapping) or not isinstance(coding.get("code"), str):
                continue
            codings.append(
                {
                    "system": str(coding.get("system") or ""),
                    "code": coding["code"],
                    "source": f"Condition/{resource.get('id')}"
                    if resource.get("id")
                    else "Condition",
                }
            )
    return codings


def code_evidence(rule: object, codings: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    icd = _normal_code(row_value(rule, "icd10_vn_1_decimal"))
    snomed = _normal_code(row_value(rule, "snomedct_2026_06_01"))
    result: list[JsonObject] = []
    for coding in codings:
        code = _normal_code(coding.get("code"))
        system = str(coding.get("system") or "").casefold()
        if not code:
            continue
        is_icd = bool(icd and code == icd and _system_matches(system, _ICD_SYSTEM_MARKERS))
        is_snomed = bool(
            snomed and code == snomed and _system_matches(system, _SNOMED_SYSTEM_MARKERS)
        )
        known_codes = {value for value in (icd, snomed) if value is not None}
        if is_icd or is_snomed or (not system and code in known_codes):
            result.append(dict(coding))
    return result


def fact_matches(runtime: Mapping[str, Any], key: str, operator: object, threshold: object) -> bool:
    value = fact(runtime, key)
    if fact_status(value) != "present":
        return False
    if operator is None or threshold is None:
        raw = fact_value(value)
        return raw is not False and raw is not None
    observed = number(runtime, key)
    if (
        observed is None
        or not isinstance(threshold, (int, float, str))
        or isinstance(threshold, bool)
    ):
        return False
    try:
        limit = float(threshold)
    except ValueError:
        return False
    return {
        "<": observed < limit,
        "<=": observed <= limit,
        ">": observed > limit,
        ">=": observed >= limit,
        "=": observed == limit,
        "==": observed == limit,
    }.get(str(operator).strip(), False)


def row_value(row: object, key: str) -> object:
    return row.get(key) if isinstance(row, Mapping) else getattr(row, key, None)


def reason_code(value: object, rule: object) -> str:
    raw = str(value or row_value(rule, "disease_finding_eng") or "CONTRAINDICATION")
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").upper()
    return normalized or "CONTRAINDICATION"


def unique_evidence(items: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    result: list[JsonObject] = []
    seen: set[str] = set()
    for item in items:
        key = repr(sorted(item.items()))
        if key not in seen:
            seen.add(key)
            result.append(dict(item))
    return result


def unique_findings(items: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    result: list[JsonObject] = []
    # A single clinical finding can intentionally produce multiple catalog
    # rows for different medicine subgroups. Keep those rows separate so the
    # final regimen removal step can remove each exact subgroup.
    seen: set[tuple[object, object, object, object, object]] = set()
    for item in items:
        key = (
            item.get("target"),
            item.get("reason_code"),
            item.get("severity"),
            item.get("drug_group"),
            item.get("drugs"),
        )
        if key not in seen:
            seen.add(key)
            result.append(dict(item))
    return result


def _normal_code(value: object) -> str | None:
    return value.strip().casefold() if isinstance(value, str) and value.strip() else None


def _system_matches(system: str, markers: Sequence[str]) -> bool:
    return any(marker in system for marker in markers)
