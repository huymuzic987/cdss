"""Focused helper rules for MRA, beta-blocker, and conduction safety."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cdss.domain.medication_safety.medication_safety_contracts import finding
from cdss.domain.medication_safety.medication_safety_inputs import (
    ABSOLUTE,
    INSUFFICIENT,
    NONSELECTIVE_BETA_BLOCKERS,
    RELATIVE,
    evidence,
    fact,
    fact_known,
    fact_value,
    number,
    present,
    target_for_medicine,
)

type JsonObject = dict[str, Any]


def mra_findings(runtime: Mapping[str, Any], output: list[JsonObject]) -> None:
    if not fact_known(runtime, "serum_potassium") or not fact_known(runtime, "eGFR"):
        output.append(
            finding(
                target="MRA",
                severity=INSUFFICIENT,
                reason_code="MRA_LABS_MISSING",
                reason_en="Recent serum potassium and eGFR are required before MRA recommendation",
                evidence=evidence(runtime, ("serum_potassium", "eGFR")),
                override_allowed=False,
            )
        )
        return
    potassium, egfr = number(runtime, "serum_potassium"), number(runtime, "eGFR")
    if potassium is None or egfr is None:
        output.append(
            finding(
                target="MRA",
                severity=INSUFFICIENT,
                reason_code="MRA_LABS_UNUSABLE",
                reason_en="Serum potassium and eGFR values cannot be used automatically",
                evidence=evidence(runtime, ("serum_potassium", "eGFR")),
                override_allowed=False,
            )
        )
    elif potassium > 4.5:
        output.append(
            finding(
                target="MRA",
                severity=ABSOLUTE,
                reason_code="MRA_INITIATION_POTASSIUM_GT_4_5",
                reason_en="Potassium is above the resistant-hypertension initiation threshold",
                evidence=evidence(runtime, ("serum_potassium",)),
                override_allowed=False,
            )
        )
    elif egfr < 30:
        output.append(
            finding(
                target="MRA",
                severity=ABSOLUTE,
                reason_code="MRA_EGFR_LT_30",
                reason_en="eGFR is below the resistant-hypertension threshold",
                evidence=evidence(runtime, ("eGFR",)),
                override_allowed=False,
            )
        )
    if _active_ras(runtime) and not present(runtime, "monitoring_plan"):
        output.append(
            finding(
                target="MRA",
                severity=INSUFFICIENT,
                reason_code="MRA_MONITORING_PLAN_MISSING",
                reason_en=(
                    "Monitoring plan is required when MRA is combined with active RAS blockade"
                ),
                evidence=[],
                override_allowed=False,
            )
        )


def _active_ras(runtime: Mapping[str, Any]) -> bool:
    active = runtime.get("active_medication_regimen")
    if not isinstance(active, (list, tuple)):
        return False
    return any(
        target_for_medicine(item) in {"ACE_INHIBITOR", "ARB"}
        for item in active
        if isinstance(item, Mapping)
    )


def beta_blocker_findings(
    runtime: Mapping[str, Any], medicine: object, output: list[JsonObject]
) -> None:
    severe = present(runtime, "active_bronchospasm") or str(
        fact_value(fact(runtime, "asthma_severity"))
    ).casefold() in {"severe", "life_threatening"}
    name = str(
        medicine.get("name", "") if isinstance(medicine, Mapping) else getattr(medicine, "name", "")
    ).casefold()
    if severe:
        output.append(
            finding(
                target="BETA_BLOCKER",
                severity=ABSOLUTE,
                reason_code="SEVERE_ASTHMA_OR_BRONCHOSPASM",
                reason_en="Active severe bronchospasm or severe asthma",
                evidence=evidence(runtime, ("active_bronchospasm", "asthma_severity")),
                override_allowed=False,
            )
        )
    elif present(runtime, "asthma_severity"):
        severity = ABSOLUTE if name in NONSELECTIVE_BETA_BLOCKERS else RELATIVE
        output.append(
            finding(
                target="BETA_BLOCKER",
                severity=severity,
                reason_code="ASTHMA_BETA_BLOCKER_REVIEW",
                reason_en="Asthma requires beta-blocker selectivity and indication review",
                evidence=evidence(runtime, ("asthma_severity",)),
                override_allowed=severity == RELATIVE,
            )
        )
    conduction_findings(runtime, "BETA_BLOCKER", output)


def conduction_findings(runtime: Mapping[str, Any], target: str, output: list[JsonObject]) -> None:
    block = str(fact_value(fact(runtime, "AV_block_grade"))).casefold()
    if block in {"2", "second", "second-degree", "3", "third", "third-degree"} and not present(
        runtime, "pacemaker_present"
    ):
        output.append(
            finding(
                target=target,
                severity=ABSOLUTE,
                reason_code="HIGH_GRADE_AV_BLOCK",
                reason_en="Second- or third-degree AV block without pacemaker",
                evidence=evidence(runtime, ("AV_block_grade", "pacemaker_present")),
                override_allowed=False,
            )
        )
    rate = number(runtime, "heart_rate")
    if rate is not None and rate < 50:
        output.append(
            finding(
                target=target,
                severity=ABSOLUTE,
                reason_code="SEVERE_BRADYCARDIA",
                reason_en="Heart rate is below 50 bpm",
                evidence=evidence(runtime, ("heart_rate",)),
                override_allowed=False,
            )
        )
    elif rate is not None and rate < 60:
        output.append(
            finding(
                target=target,
                severity=RELATIVE,
                reason_code="BRADYCARDIA",
                reason_en="Heart rate is below 60 bpm",
                evidence=evidence(runtime, ("heart_rate",)),
                override_allowed=True,
            )
        )
    if target == "NON_DIHYDROPYRIDINE_CCB":
        lvef = number(runtime, "LVEF")
        if lvef is not None and lvef < 40:
            output.append(
                finding(
                    target=target,
                    severity=ABSOLUTE,
                    reason_code="SEVERE_LV_DYSFUNCTION",
                    reason_en="LVEF is below 40%",
                    evidence=evidence(runtime, ("LVEF",)),
                    override_allowed=False,
                )
            )
