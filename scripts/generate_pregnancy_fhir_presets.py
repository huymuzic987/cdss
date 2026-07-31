"""Generate deterministic, schema-valid FHIR R4 pregnancy simulator presets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "fhir" / "pregnancy_presets"

BASE_URL = "http://example.org/fhir"
EXT_BASE = "http://cdss.local/fhir/StructureDefinition"
INPUT_EXTENSION = f"{EXT_BASE}/input"
READING_ROLE_EXTENSION = f"{EXT_BASE}/reading-role"
RISK_FACTOR_EXTENSION = f"{EXT_BASE}/risk-factor-count"
CLINICAL_FLAG_SYSTEM = "http://cdss.local/fhir/CodeSystem/clinical-flag"
PRESET_META_BASE = "http://cdss.local/fhir/CodeSystem/preset"

PREGNANCY_CATEGORY = "Pregnancy & Postpartum"
FOLLOW_UP_CATEGORY = "Pregnancy Follow-Up Sequence"


@dataclass(frozen=True, slots=True)
class Visit:
    suffix: str
    date: str
    sbp: int
    dbp: int


@dataclass(frozen=True, slots=True)
class PresetCase:
    preset_id: str
    label: str
    description: str
    clinic_bp: tuple[int, int]
    home_bp: tuple[int, int] = (120, 75)
    flags: tuple[str, ...] = ("is_pregnant",)
    inputs: dict[str, int | str] = field(default_factory=dict)
    proteinuria_24h_mg: int = 50
    acr_mg_mmol: int = 5
    expected_terminal: str = ""
    expected_nodes: tuple[str, ...] = ()
    category: str = PREGNANCY_CATEGORY
    visits: tuple[Visit, ...] = ()
    patient_id: str | None = None


def _static_cases() -> list[PresetCase]:
    return [
        PresetCase(
            "pregnancy-normotensive-monitor",
            "Pregnancy — Normotensive Monitoring",
            "Normal home and clinic BP; reaches the pregnancy monitoring terminal.",
            (120, 75),
            expected_terminal="T12_END_FOLLOW_UP_MONITOR",
            expected_nodes=("T12_C_CLINIC_BP_NORMAL",),
        ),
        PresetCase(
            "pregnancy-high-preeclampsia-risk-aspirin",
            "Pregnancy — High Preeclampsia Risk (Aspirin)",
            "Normotensive high-risk pregnancy; reaches aspirin prophylaxis.",
            (130, 80),
            (118, 75),
            ("is_pregnant", "has_high_preeclampsia_risk"),
            expected_terminal="T12_END_ASPIRIN_PROPHYLAXIS",
            expected_nodes=("T12_C_HIGH_PREECLAMPSIA_RISK",),
        ),
        PresetCase(
            "pregnancy-chronic-htn",
            "Pregnancy — Pre-Existing (Chronic) Hypertension",
            "Pre-pregnancy hypertension with proteinuria persisting beyond six weeks.",
            (150, 95),
            flags=("is_pregnant", "has_pre_pregnancy_hypertension", "has_proteinuria"),
            inputs={"weeks_persisting_postpartum": 8, "weeks_resolved_postpartum": 10},
            proteinuria_24h_mg=100,
            expected_terminal="T12_END_PRE_EXISTING_HTN",
            expected_nodes=("T12_C_CHRONIC_HTN",),
        ),
        PresetCase(
            "pregnancy-gestational-mild",
            "Pregnancy — Gestational Hypertension, Mild/Moderate (Refer)",
            (
                "Clinic-only mild/moderate gestational hypertension outside the "
                "narrow treatment target."
            ),
            (150, 95),
            flags=("is_pregnant", "has_hypertension_after_week_20"),
            expected_terminal="T12_END_REFER_OBGYN",
            expected_nodes=(
                "T12_C_CLINIC_BP_HIGH",
                "T12_INF_GESTATIONAL_HTN_CLASSIFICATION",
                "T12_C_BP_MILD_MODERATE",
                "T12_C_BP_TARGET_NOT_ACHIEVED",
            ),
        ),
        PresetCase(
            "pregnancy-bp-target-achieved",
            "Pregnancy — Gestational Hypertension via Home BP (Maintain)",
            (
                "High home BP enters Tree 12 while clinic BP is exactly in the "
                "pregnancy treatment target."
            ),
            (140, 85),
            (138, 87),
            ("is_pregnant", "has_hypertension_after_week_20"),
            expected_terminal="T12_END_MAINTAIN_REGIMEN_PREGNANT",
            expected_nodes=(
                "T12_C_HOME_BP_HIGH",
                "T12_C_BP_MILD_MODERATE",
                "T12_C_BP_TARGET_ACHIEVED",
            ),
        ),
        PresetCase(
            "pregnancy-gestational-severe-crisis",
            "Pregnancy — Severe Gestational HTN with Hypertensive Crisis",
            "Severe gestational hypertension through the hypertensive-crisis treatment branch.",
            (165, 110),
            flags=(
                "is_pregnant",
                "has_hypertension_after_week_20",
                "has_hypertensive_crisis",
            ),
            expected_terminal="T12_END_REFER_OBGYN",
            expected_nodes=(
                "T12_C_BP_SEVERE",
                "T12_C_HYPERTENSIVE_CRISIS",
                "T12_INF_IV_NITROGLYCERIN",
            ),
        ),
        PresetCase(
            "pregnancy-gestational-severe-pulmonary-edema",
            "Pregnancy — Severe Gestational HTN with Pulmonary Edema",
            "Severe gestational hypertension through the pulmonary-edema treatment branch.",
            (165, 110),
            flags=(
                "is_pregnant",
                "has_hypertension_after_week_20",
                "has_pulmonary_edema",
            ),
            expected_terminal="T12_END_REFER_OBGYN",
            expected_nodes=(
                "T12_C_BP_SEVERE",
                "T12_C_PULMONARY_EDEMA",
                "T12_INF_MAGNESIUM_SUPPLEMENT",
            ),
        ),
        PresetCase(
            "pregnancy-preeclampsia-protein-target-met",
            "Pregnancy — Preeclampsia by 24-Hour Protein (Target Met)",
            (
                "Preeclampsia from proteinuria above 300 mg/24 h; immediate and "
                "pregnancy targets are met."
            ),
            (140, 85),
            flags=("is_pregnant", "has_hypertension_after_week_20", "has_proteinuria"),
            proteinuria_24h_mg=350,
            expected_terminal="T12_END_MAINTAIN_REGIMEN_PREGNANT",
            expected_nodes=(
                "T12_C_PREECLAMPSIA_PROTEINURIA",
                "T12_INF_PREECLAMPSIA_CLASSIFICATION",
                "T12_C_TARGET_MET",
            ),
        ),
        PresetCase(
            "pregnancy-preeclampsia-acr-target-not-met",
            "Pregnancy — Preeclampsia by ACR (Emergency Delivery)",
            "Preeclampsia from ACR above 30 mg/mmol with the immediate BP target not met.",
            (165, 110),
            flags=("is_pregnant", "has_hypertension_after_week_20", "has_proteinuria"),
            acr_mg_mmol=35,
            expected_terminal="T12_END_EMERGENCY_DELIVERY",
            expected_nodes=(
                "T12_C_PREECLAMPSIA_PROTEINURIA",
                "T12_C_TARGET_NOT_MET",
            ),
        ),
        PresetCase(
            "pregnancy-preeclampsia-risk-factor",
            "Pregnancy — Preeclampsia by Risk Factor (Target Met)",
            "Gestational hypertension with diabetes as a preeclampsia risk factor.",
            (140, 85),
            flags=("is_pregnant", "has_hypertension_after_week_20", "has_diabetes"),
            expected_terminal="T12_END_MAINTAIN_REGIMEN_PREGNANT",
            expected_nodes=(
                "T12_C_PREECLAMPSIA_RISK_FACTOR",
                "T12_INF_PREECLAMPSIA_CLASSIFICATION",
                "T12_C_TARGET_MET",
            ),
        ),
        PresetCase(
            "pregnancy-eclampsia-target-met",
            "Pregnancy — Eclampsia (Immediate Target Met)",
            "Preeclampsia with seizure, without visual disturbance or coagulopathy; target is met.",
            (140, 85),
            flags=(
                "is_pregnant",
                "has_hypertension_after_week_20",
                "has_proteinuria",
                "has_seizure",
            ),
            proteinuria_24h_mg=350,
            expected_terminal="T12_END_MAINTAIN_REGIMEN_PREGNANT",
            expected_nodes=(
                "T12_C_SEVERE_SIGNS",
                "T12_INF_ECLAMPSIA_CLASSIFICATION",
                "T12_C_TARGET_MET",
            ),
        ),
        PresetCase(
            "pregnancy-severe-eclampsia",
            "Pregnancy — Eclampsia (Emergency Delivery)",
            "Preeclampsia with seizure and an immediate BP target that is not met.",
            (165, 110),
            flags=(
                "is_pregnant",
                "has_hypertension_after_week_20",
                "has_proteinuria",
                "has_seizure",
            ),
            proteinuria_24h_mg=350,
            expected_terminal="T12_END_EMERGENCY_DELIVERY",
            expected_nodes=(
                "T12_C_SEVERE_SIGNS",
                "T12_INF_ECLAMPSIA_CLASSIFICATION",
                "T12_C_TARGET_NOT_MET",
            ),
        ),
        PresetCase(
            "pregnancy-hellp-target-met",
            "Pregnancy — HELLP Syndrome (Immediate Target Met)",
            "HELLP triad with BP below the immediate ceiling and at the pregnancy target.",
            (140, 85),
            flags=(
                "is_pregnant",
                "has_hypertension_after_week_20",
                "has_hemolysis",
                "has_elevated_liver_enzymes",
                "has_low_platelets",
            ),
            expected_terminal="T12_END_MAINTAIN_REGIMEN_PREGNANT",
            expected_nodes=(
                "T12_C_HELLP_SIGNS",
                "T12_INF_HELLP_SYNDROME_CLASSIFICATION",
                "T12_C_TARGET_MET",
            ),
        ),
        PresetCase(
            "pregnancy-hellp-target-not-met",
            "Pregnancy — HELLP Syndrome (Emergency Delivery)",
            "HELLP triad with the immediate BP target not met.",
            (165, 110),
            flags=(
                "is_pregnant",
                "has_hypertension_after_week_20",
                "has_hemolysis",
                "has_elevated_liver_enzymes",
                "has_low_platelets",
            ),
            expected_terminal="T12_END_EMERGENCY_DELIVERY",
            expected_nodes=(
                "T12_C_HELLP_SIGNS",
                "T12_INF_HELLP_SYNDROME_CLASSIFICATION",
                "T12_C_TARGET_NOT_MET",
            ),
        ),
        PresetCase(
            "pregnancy-postpartum-breastfeeding",
            "Postpartum — Breastfeeding Guidance",
            (
                "Postpartum patient who is breastfeeding; reaches the "
                "breastfeeding medication guidance."
            ),
            (145, 95),
            flags=("is_postpartum", "is_breastfeeding"),
            expected_terminal="T12_END_MAINTAIN_REGIMEN_POSTPARTUM",
            expected_nodes=("T12_C_POSTPARTUM", "T12_C_BREASTFEEDING"),
        ),
        PresetCase(
            "pregnancy-postpartum-bp-high",
            "Postpartum — BP Still High",
            "Postpartum BP remains at or above 140/90 and the regimen excludes methyldopa.",
            (145, 95),
            flags=("is_postpartum",),
            expected_terminal="T12_END_MAINTAIN_REGIMEN_POSTPARTUM",
            expected_nodes=("T12_C_POSTPARTUM", "T12_C_BP_STILL_HIGH"),
        ),
        PresetCase(
            "pregnancy-postpartum-bp-normal",
            "Postpartum — BP No Longer High",
            "Postpartum BP is below 140/90 and the maintenance terminal is reached directly.",
            (130, 80),
            flags=("is_postpartum",),
            expected_terminal="T12_END_MAINTAIN_REGIMEN_POSTPARTUM",
            expected_nodes=("T12_C_POSTPARTUM", "T12_C_BP_NOT_HIGH"),
        ),
    ]


def _follow_up_cases() -> list[PresetCase]:
    visits = (
        Visit("initial", "2026-01-05", 150, 95),
        Visit("follow-up-1", "2026-01-26", 140, 85),
        Visit("follow-up-2", "2026-02-16", 140, 85),
        Visit("follow-up-3", "2026-03-09", 142, 92),
    )
    labels = (
        "Pregnancy Episode — Initial Visit",
        "Pregnancy Episode — Follow-Up 1",
        "Pregnancy Episode — Follow-Up 2",
        "Pregnancy Episode — Follow-Up 3 Postpartum (Minimum Complete)",
    )
    terminals = (
        "T12_END_REFER_OBGYN",
        "T12_END_MAINTAIN_REGIMEN_PREGNANT",
        "T12_END_MAINTAIN_REGIMEN_PREGNANT",
        "T12_END_MAINTAIN_REGIMEN_POSTPARTUM",
    )
    cases: list[PresetCase] = []
    for follow_up_number, (label, terminal) in enumerate(zip(labels, terminals, strict=True)):
        postpartum = follow_up_number == 3
        cases.append(
            PresetCase(
                preset_id=f"pregnancy-episode-follow-up-{follow_up_number}",
                label=label,
                description=(
                    f"Longitudinal pregnancy episode with {follow_up_number + 1} "
                    f"FHIR Encounter resource(s); follow-up number {follow_up_number}."
                ),
                clinic_bp=(visits[follow_up_number].sbp, visits[follow_up_number].dbp),
                home_bp=(138, 87),
                flags=(
                    ("is_postpartum", "is_breastfeeding", "has_hypertension_after_week_20")
                    if postpartum
                    else ("is_pregnant", "has_hypertension_after_week_20")
                ),
                inputs={
                    "pregnancy_episode_id": "pregnancy-demo-001",
                    "pregnancy_follow_up_number": follow_up_number,
                },
                expected_terminal=terminal,
                expected_nodes=(
                    ("T12_C_POSTPARTUM", "T12_C_BREASTFEEDING")
                    if postpartum
                    else ("T12_INF_GESTATIONAL_HTN_CLASSIFICATION",)
                ),
                category=FOLLOW_UP_CATEGORY,
                visits=visits[: follow_up_number + 1],
                patient_id="PGF001",
            )
        )
    return cases


def _extension(key: str, value: int | str) -> dict[str, Any]:
    typed_key = "valueInteger" if isinstance(value, int) else "valueString"
    return {"url": f"{INPUT_EXTENSION}/{key}", typed_key: value}


def _entry(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "fullUrl": f"{BASE_URL}/{resource['resourceType']}/{resource['id']}",
        "resource": resource,
    }


def _condition(patient_id: str, flag: str) -> dict[str, Any]:
    condition_id = f"{patient_id}-{flag.replace('_', '-')}"
    return {
        "resourceType": "Condition",
        "id": condition_id,
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                }
            ]
        },
        "code": {
            "coding": [{"system": CLINICAL_FLAG_SYSTEM, "code": flag}],
            "text": flag.replace("_", " ").title(),
        },
        "subject": {"reference": f"Patient/{patient_id}"},
    }


def _observation(
    patient_id: str,
    observation_id: str,
    code: str,
    display: str,
    value: int,
    unit: str,
    ucum_code: str,
    date: str,
    *,
    category: str,
    encounter_id: str | None = None,
    reading_role: str | None = None,
) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": category,
                    }
                ]
            }
        ],
        "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": f"{date}T08:00:00+07:00",
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": ucum_code,
        },
    }
    if encounter_id:
        resource["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    if reading_role:
        resource["extension"] = [{"url": READING_ROLE_EXTENSION, "valueCode": reading_role}]
    return resource


def _encounter(patient_id: str, visit: Visit) -> dict[str, Any]:
    encounter_id = f"{patient_id}-{visit.suffix}"
    return {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {
            "start": f"{visit.date}T08:00:00+07:00",
            "end": f"{visit.date}T08:30:00+07:00",
        },
    }


def _metadata(case: PresetCase) -> dict[str, Any]:
    tags = [
        {
            "system": f"{PRESET_META_BASE}/category",
            "code": ("pregnancy-follow-up" if case.category == FOLLOW_UP_CATEGORY else "pregnancy"),
            "display": case.category,
        },
        {
            "system": f"{PRESET_META_BASE}/description",
            "code": case.preset_id,
            "display": case.description,
        },
        {
            "system": f"{PRESET_META_BASE}/label",
            "code": case.preset_id,
            "display": case.label,
        },
        {
            "system": f"{PRESET_META_BASE}/expected-terminal",
            "code": case.expected_terminal,
        },
    ]
    tags.extend(
        {
            "system": f"{PRESET_META_BASE}/expected-node",
            "code": node_key,
        }
        for node_key in case.expected_nodes
    )
    return {"tag": tags}


def _bundle(case: PresetCase, index: int) -> dict[str, Any]:
    patient_id = case.patient_id or f"PG{index:03d}"
    inputs: dict[str, int | str] = {
        "weeks_persisting_postpartum": 0,
        "weeks_resolved_postpartum": 2,
        **case.inputs,
    }
    patient_extensions = [
        {"url": RISK_FACTOR_EXTENSION, "valueInteger": 1},
        *(_extension(key, value) for key, value in inputs.items()),
    ]
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "gender": "female",
        "birthDate": "1997-04-12",
        "extension": patient_extensions,
        "address": [
            {
                "use": "home",
                "type": "physical",
                "city": "Ho Chi Minh City",
                "country": "VN",
            }
        ],
    }
    entries = [_entry(patient)]
    entries.extend(_entry(_condition(patient_id, flag)) for flag in case.flags)

    latest_date = case.visits[-1].date if case.visits else "2026-01-05"
    if case.visits:
        for visit in case.visits:
            encounter = _encounter(patient_id, visit)
            entries.append(_entry(encounter))
            encounter_id = str(encounter["id"])
            entries.extend(
                [
                    _entry(
                        _observation(
                            patient_id,
                            f"{encounter_id}-sbp",
                            "8459-0",
                            "Sitting systolic blood pressure",
                            visit.sbp,
                            "mmHg",
                            "mm[Hg]",
                            visit.date,
                            category="vital-signs",
                            encounter_id=encounter_id,
                        )
                    ),
                    _entry(
                        _observation(
                            patient_id,
                            f"{encounter_id}-dbp",
                            "8462-4",
                            "Diastolic blood pressure",
                            visit.dbp,
                            "mmHg",
                            "mm[Hg]",
                            visit.date,
                            category="vital-signs",
                            encounter_id=encounter_id,
                        )
                    ),
                ]
            )
    else:
        clinic_sbp, clinic_dbp = case.clinic_bp
        entries.extend(
            [
                _entry(
                    _observation(
                        patient_id,
                        f"{patient_id}-clinic-sbp",
                        "8459-0",
                        "Sitting systolic blood pressure",
                        clinic_sbp,
                        "mmHg",
                        "mm[Hg]",
                        latest_date,
                        category="vital-signs",
                        reading_role="current_clinic",
                    )
                ),
                _entry(
                    _observation(
                        patient_id,
                        f"{patient_id}-clinic-dbp",
                        "8462-4",
                        "Diastolic blood pressure",
                        clinic_dbp,
                        "mmHg",
                        "mm[Hg]",
                        latest_date,
                        category="vital-signs",
                        reading_role="current_clinic",
                    )
                ),
            ]
        )

    home_sbp, home_dbp = case.home_bp
    entries.extend(
        [
            _entry(
                _observation(
                    patient_id,
                    f"{patient_id}-home-sbp",
                    "8459-0",
                    "Home systolic blood pressure",
                    home_sbp,
                    "mmHg",
                    "mm[Hg]",
                    latest_date,
                    category="vital-signs",
                    reading_role="home",
                )
            ),
            _entry(
                _observation(
                    patient_id,
                    f"{patient_id}-home-dbp",
                    "8462-4",
                    "Home diastolic blood pressure",
                    home_dbp,
                    "mmHg",
                    "mm[Hg]",
                    latest_date,
                    category="vital-signs",
                    reading_role="home",
                )
            ),
            _entry(
                _observation(
                    patient_id,
                    f"{patient_id}-proteinuria",
                    "2889-4",
                    "Protein [Mass/time] in 24 hour Urine",
                    case.proteinuria_24h_mg,
                    "mg/24 h",
                    "mg/(24.h)",
                    latest_date,
                    category="laboratory",
                )
            ),
            _entry(
                _observation(
                    patient_id,
                    f"{patient_id}-acr",
                    "9318-7",
                    "Albumin/Creatinine [Ratio] in Urine",
                    case.acr_mg_mmol,
                    "mg/mmol",
                    "mg/mmol",
                    latest_date,
                    category="laboratory",
                )
            ),
        ]
    )

    follow_up_suffix = (
        f"-fu{case.inputs['pregnancy_follow_up_number']}"
        if "pregnancy_follow_up_number" in case.inputs
        else ""
    )
    return {
        "resourceType": "Bundle",
        "id": f"bundle-{patient_id}{follow_up_suffix}",
        "meta": _metadata(case),
        "identifier": {
            "system": f"{PRESET_META_BASE}/id",
            "value": case.preset_id,
        },
        "type": "collection",
        "timestamp": f"{latest_date}T08:00:00+07:00",
        "entry": entries,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = [*_static_cases(), *_follow_up_cases()]
    expected_files: set[Path] = set()
    for index, case in enumerate(cases, start=1):
        path = OUTPUT_DIR / f"{index:02d}-{case.preset_id}.json"
        path.write_text(
            json.dumps(_bundle(case, index), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        expected_files.add(path)

    stale_files = set(OUTPUT_DIR.glob("*.json")) - expected_files
    if stale_files:
        names = ", ".join(sorted(path.name for path in stale_files))
        raise RuntimeError(f"Remove stale generated pregnancy preset files: {names}")
    print(f"Generated {len(cases)} FHIR R4 pregnancy presets in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
