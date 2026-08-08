"""Small JSON contracts shared by medication-safety evaluation and presentation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

type JsonObject = dict[str, Any]

type FactStatus = Literal["present", "absent", "unknown", "conflicting"]
type SafetySeverity = Literal[
    "ABSOLUTE",
    "INSUFFICIENT_DATA",
    "RELATIVE",
    "ELIGIBLE",
    "PREFERRED",
]

RULESET_ID = "HTN_VNHA_2022_REVIEWED_2026_01"


def unknown_fact() -> JsonObject:
    """Return an explicit unknown fact rather than silently using False."""

    return {"status": "unknown", "evidence": []}


def fact_value(fact: object) -> object:
    if isinstance(fact, Mapping):
        return fact.get("value")
    return None


def fact_status(fact: object) -> FactStatus:
    if isinstance(fact, Mapping) and fact.get("status") in {
        "present",
        "absent",
        "unknown",
        "conflicting",
    }:
        return fact["status"]  # type: ignore[return-value]
    return "unknown"


def finding(
    *,
    target: str,
    severity: SafetySeverity,
    reason_code: str,
    reason_en: str,
    evidence: object = None,
    override_allowed: bool | None = None,
) -> JsonObject:
    """Build the stable safety-finding shape exposed in API responses."""

    item: JsonObject = {
        "target": target,
        "severity": severity,
        "reason_code": reason_code,
        "reason_en": reason_en,
        "evidence": evidence if isinstance(evidence, list) else [],
    }
    if override_allowed is not None:
        item["override_allowed"] = override_allowed
    return item
