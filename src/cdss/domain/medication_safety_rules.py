"""Target-level safety rules; this module does not know about tree traversal."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from cdss.domain.medication_safety_contracts import finding
from cdss.domain.medication_safety_inputs import (
    ABSOLUTE,
    INSUFFICIENT,
    RELATIVE,
    evidence,
    present,
    target_for_medicine,
)
from cdss.domain.medication_safety_rule_helpers import (
    beta_blocker_findings,
    conduction_findings,
    mra_findings,
)

if TYPE_CHECKING:
    from cdss.domain.decision_tree.medicine_catalog import Medicine

type JsonObject = dict[str, Any]


def evaluate_target(
    target: str,
    runtime: Mapping[str, Any],
    *,
    medicine: Medicine | Mapping[str, Any] | None = None,
    clinical_context: str = "chronic_hypertension",
) -> JsonObject:
    """Evaluate one target. Relative findings remain selectable with review."""

    target = target_for_medicine(medicine, target) if medicine is not None else target
    findings: list[JsonObject] = []
    pregnancy = present(runtime, "pregnancy_status")
    pregnancy_evidence = evidence(runtime, ("pregnancy_status",))
    if pregnancy and target in {"ACE_INHIBITOR", "ARB", "DIRECT_RENIN_INHIBITOR", "MRA"}:
        findings.append(
            finding(
                target=target,
                severity=ABSOLUTE,
                reason_code="PREGNANCY",
                reason_en="Pregnancy",
                evidence=pregnancy_evidence,
                override_allowed=False,
            )
        )
    if pregnancy and target == "THIAZIDE_LIKE_DIURETIC":
        findings.append(
            finding(
                target=target,
                severity=RELATIVE,
                reason_code="PREGNANCY_THIAZIDE_REVIEW",
                reason_en="Pregnancy requires an alternative or specialist review",
                evidence=pregnancy_evidence,
                override_allowed=True,
            )
        )
    if pregnancy and target == "NICARDIPINE" and clinical_context != "acute_emergency":
        findings.append(
            finding(
                target=target,
                severity=RELATIVE,
                reason_code="PREGNANCY_NICARDIPINE_REVIEW",
                reason_en="Nicardipine requires pregnancy-specific route and indication review",
                evidence=pregnancy_evidence,
                override_allowed=True,
            )
        )
    if target == "ACE_INHIBITOR" and present(runtime, "angioedema_history"):
        findings.append(
            finding(
                target=target,
                severity=ABSOLUTE,
                reason_code="ANGIOEDEMA_HISTORY",
                reason_en="History of angioedema",
                evidence=evidence(runtime, ("angioedema_history",)),
                override_allowed=False,
            )
        )
    if target in {"ACE_INHIBITOR", "ARB"} and present(runtime, "renal_artery_stenosis"):
        findings.append(
            finding(
                target=target,
                severity=ABSOLUTE,
                reason_code="BILATERAL_RENAL_ARTERY_STENOSIS",
                reason_en="Bilateral renal artery stenosis",
                evidence=evidence(runtime, ("renal_artery_stenosis",)),
                override_allowed=False,
            )
        )
    if target == "MRA":
        mra_findings(runtime, findings)
    elif target == "BETA_BLOCKER":
        beta_blocker_findings(runtime, medicine, findings)
    elif target == "NON_DIHYDROPYRIDINE_CCB":
        conduction_findings(runtime, target, findings)
    elif target == "THIAZIDE_LIKE_DIURETIC":
        for key, code, reason in (
            ("gout_status", "GOUT", "Gout"),
            ("hypercalcaemia", "HYPERCALCAEMIA", "Hypercalcaemia"),
            ("hypokalaemia", "HYPOKALAEMIA", "Hypokalaemia"),
        ):
            if present(runtime, key):
                findings.append(
                    finding(
                        target=target,
                        severity=RELATIVE,
                        reason_code=code,
                        reason_en=reason + " may be worsened by thiazide therapy",
                        evidence=evidence(runtime, (key,)),
                        override_allowed=True,
                    )
                )
    return {"target": target, "status": _severity(findings), "findings": findings}


def _severity(findings: Sequence[Mapping[str, Any]]) -> str:
    for severity in (ABSOLUTE, INSUFFICIENT, RELATIVE):
        if any(item.get("severity") == severity for item in findings):
            return severity
    return "ELIGIBLE"
