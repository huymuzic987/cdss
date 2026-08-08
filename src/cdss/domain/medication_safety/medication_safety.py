"""Structured medication-safety gate used by every medication-producing tree."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from cdss.domain.medication_safety.medication_safety_contracts import RULESET_ID, fact_status
from cdss.domain.medication_safety.medication_safety_inputs import facts, target_for_medicine
from cdss.domain.medication_safety.medication_safety_interactions import (
    regimen_interaction_findings,
)
from cdss.domain.medication_safety.medication_safety_rules import evaluate_target

if TYPE_CHECKING:
    from cdss.domain.decision_tree.medicine_catalog import Medicine

type JsonObject = dict[str, Any]


def evaluate_medication_safety(
    runtime: Mapping[str, Any],
    targets: Sequence[str] = (),
    *,
    medicines: Sequence[Medicine | Mapping[str, Any]] = (),
    clinical_context: str = "chronic_hypertension",
) -> JsonObject:
    """Evaluate targets and return findings, blocked targets, and review targets."""

    evaluations = [
        evaluate_target(target, runtime, clinical_context=clinical_context)
        for target in dict.fromkeys(targets)
    ]
    evaluations.extend(
        evaluate_target(
            target_for_medicine(medicine),
            runtime,
            medicine=medicine,
            clinical_context=clinical_context,
        )
        for medicine in medicines
    )
    findings = [item for result in evaluations for item in result["findings"]]
    findings.extend(
        regimen_interaction_findings([item for item in medicines if isinstance(item, Mapping)])
    )
    blocked = sorted({str(item["target"]) for item in findings if item["severity"] == "ABSOLUTE"})
    review = sorted(
        {
            str(item["target"])
            for item in findings
            if item["severity"] in {"INSUFFICIENT_DATA", "RELATIVE"}
        }
    )
    conflicting = any(
        fact_status(value) == "conflicting"
        for value in facts(runtime).values()
        if isinstance(value, Mapping)
    )
    return {
        "status": "NEEDS_REVIEW"
        if conflicting or any(item["severity"] == "INSUFFICIENT_DATA" for item in findings)
        else "COMPLETE",
        "ruleset_id": RULESET_ID,
        "findings": findings,
        "blocked_targets": blocked,
        "review_targets": review,
    }
