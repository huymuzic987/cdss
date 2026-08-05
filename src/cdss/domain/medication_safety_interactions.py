"""Small interaction checks for active regimens and explicit combinations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cdss.domain.medication_safety_contracts import finding
from cdss.domain.medication_safety_inputs import target_for_medicine

type JsonObject = dict[str, Any]


def dual_ras_blockade_finding() -> JsonObject:
    return finding(
        target="RAS_COMBINATION",
        severity="ABSOLUTE",
        reason_code="DUAL_RAS_BLOCKADE",
        reason_en="ACE inhibitor and ARB should not be combined",
        evidence=[],
        override_allowed=False,
    )


def regimen_interaction_findings(
    medicines: Sequence[Mapping[str, Any]],
) -> list[JsonObject]:
    targets = {target_for_medicine(item) for item in medicines}
    if {"ACE_INHIBITOR", "ARB"}.issubset(targets):
        result = dual_ras_blockade_finding()
        result["evidence"] = [
            {"source": item["source_reference"]}
            for item in medicines
            if isinstance(item.get("source_reference"), str)
        ]
        return [result]
    return []
