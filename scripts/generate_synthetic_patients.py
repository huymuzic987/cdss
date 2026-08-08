"""Generate synthetic FHIR R4 patient data for the statistics dashboard.

Produces two Bundle JSON files under data/fhir/:
  - preset_patients.json    (small, fixed-seed set for demos/tests)
  - synthetic_patients.json (1000 patients, fixed-seed, randomized specs)

Shaped to match the project's real reference data (backups/test_case/*.json):
LOINC 8459-0 for sitting SBP (not the generic 8480-6), eGFR + potassium labs,
ICD-10-coded Condition resources, real drug names/doses drawn from the seeded
`medicines` table, and the ai4life extension namespace for department/
cdss-adherent. On top of that shared vocabulary, every patient gets an
initial encounter plus 3-5 follow-up encounters (so the CDSS can be
exercised on >=3 follow-up visits per patient) -- something the single-
snapshot reference data doesn't cover. Each follow-up has a chance of being
an early revisit (before the scheduled recheck date) with a reason
(medication not suitable / condition worsened / side effects / other), and
each visit records what the CDSS would recommend vs. what was actually
prescribed, so the dashboard can compare adherent vs. non-adherent outcomes.

Reads the real medicines catalog from the database (drug names must match
what clinical_import.py's name-based matching expects) but writes a fully
static, standalone JSON file -- no runtime DB dependency for consumers.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

from cdss.core.database import get_session_factory
from cdss.infrastructure.db.models import Medicine

EXT_BASE = "http://cdss.local/fhir/StructureDefinition"
AI4LIFE_BASE = "http://example.org/fhir/ai4life/StructureDefinition"
CS_ICD10 = "http://hl7.org/fhir/sid/icd-10"
CS_SNOMED = "http://snomed.info/sct"
SYS_LOINC = "http://loinc.org"
SYS_UCUM = "http://unitsofmeasure.org"

REFERENCE_DATE = date(2026, 7, 24)

# (icd10, snomed, vietnamese text) -- snomed codes reused from backups/test_case
# where available (CKD); the rest are well-known standard SNOMED CT concepts.
COMORBIDITIES = {
    "TYPE_2_DIABETES": ("E11", "44054006", "Đái tháo đường típ 2"),
    "CKD": ("N18", "709044004", "Bệnh thận mạn"),
    "CORONARY_ARTERY_DISEASE": ("I25", "53741008", "Bệnh mạch vành"),
    "HEART_FAILURE": ("I50", "84114007", "Suy tim"),
    "STROKE": ("I63", "422504002", "Đột quỵ thiếu máu não"),
}
HYPERTENSION_ICD10 = ("I10", "38341003", "THA nguyên phát")

DEPARTMENTS = [
    ("Ngoại trú", 0.45),
    ("Nội tim mạch", 0.42),
    ("Nội thận", 0.08),
    ("Cấp cứu", 0.05),
]

EARLY_REVISIT_REASONS = [
    ("MEDICATION_NOT_SUITABLE", 0.40),
    ("CONDITION_WORSENED", 0.30),
    ("SIDE_EFFECTS", 0.20),
    ("OTHER", 0.10),
]
HYPERTENSION_BUCKETS = [
    # (class, sbp_range, dbp_range, weight)
    ("NORMAL_BP", (108, 119), (68, 79), 0.05),
    ("HIGH_NORMAL_BP", (120, 139), (80, 89), 0.15),
    ("GRADE_1_HYPERTENSION", (140, 159), (90, 99), 0.45),
    ("GRADE_2_HYPERTENSION", (160, 190), (100, 118), 0.35),
]

_DOSE_RANGE_MG = {"A": (10, 40), "B": (25, 100), "C": (5, 10), "D": (12.5, 25)}


def _weighted_choice(options: list[tuple[Any, float]]) -> Any:
    total = sum(weight for _, weight in options)
    roll = random.random() * total
    upto = 0.0
    for value, weight in options:
        upto += weight
        if roll <= upto:
            return value
    return options[-1][0]


def _load_medicines_by_class() -> dict[str, list[tuple[str, str]]]:
    session = get_session_factory()()
    try:
        rows = session.execute(
            select(Medicine.drug_id, Medicine.name, Medicine.drug_class).where(
                Medicine.drug_class.in_(["A", "B", "C", "D"])
            )
        ).all()
    finally:
        session.close()
    by_class: dict[str, list[tuple[str, str]]] = {"A": [], "B": [], "C": [], "D": []}
    for drug_id, name, drug_class in rows:
        by_class[drug_class].append((drug_id, name))
    return by_class


def _target_classes(
    hypertension_class: str, facility_capability: str, visits_uncontrolled: int
) -> list[str]:
    """Drug classes to initiate for a patient who is *not yet* at target.
    ``visits_uncontrolled`` is how many consecutive visits (including this
    one) they've gone without reaching it -- monotherapy escalates to a
    two-drug combination after two straight misses, same combination already
    used for Grade 2 from the start. Callers handle the "already controlled,
    maintain the existing regimen" case separately -- this function is only
    about what to escalate *to*, never about dropping a working regimen.
    """
    if hypertension_class in ("NORMAL_BP", "HIGH_NORMAL_BP"):
        return []
    combo = ["D", "C"] if facility_capability == "LIMITED_RESOURCES" else ["A", "C"]
    if hypertension_class == "GRADE_1_HYPERTENSION" and visits_uncontrolled < 2:
        return ["C"]
    return combo


def _recommended_action_text(
    classes: list[str], *, bp_controlled: bool, has_active_regimen: bool
) -> str:
    if bp_controlled:
        return (
            "Maintain current regimen"
            if has_active_regimen
            else "Lifestyle modification only, reassess in 3-6 months"
        )
    if not classes:
        return "Lifestyle modification only, reassess in 3-6 months"
    if len(classes) == 1:
        return "Lifestyle modification + initiate CCB monotherapy"
    lead = "thiazide-like diuretic" if classes[0] == "D" else "ACEI/ARB"
    return f"Lifestyle modification + initiate two-drug combination ({lead} + CCB)"


@dataclass
class VisitRecord:
    visit_number: int
    visit_date: date
    is_early_revisit: bool
    early_revisit_reason: str | None
    facility_capability: str
    clinic_sbp: int
    clinic_dbp: int
    egfr: float
    potassium: float
    bp_target_sbp: int
    bp_target_dbp: int
    bp_controlled: bool
    hypertension_class: str | None
    risk_level: str
    cdss_recommended_action: str
    actual_drugs: list[tuple[str, str, float]]  # (drug_id, name, dose_mg)
    adherent_to_cdss: bool
    scheduled_next_visit_date: date


@dataclass
class PatientRecord:
    fhir_id: str
    gender: str
    birth_date: date
    risk_factor_count: int
    department: str
    comorbidities: list[str]
    visits: list[VisitRecord] = field(default_factory=list)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _generate_patient(
    index: int,
    prefix: str,
    adherence_rate: float,
    medicines_by_class: dict[str, list[tuple[str, str]]],
) -> PatientRecord:
    age = random.randint(30, 85)
    gender = random.choice(["male", "female"])
    birth_date = REFERENCE_DATE.replace(year=REFERENCE_DATE.year - age)
    risk_factor_count = random.randint(0, 6)
    comorbidities = [code for code in COMORBIDITIES if random.random() < 0.15]
    has_ckd = "CKD" in comorbidities
    department = "Nội thận" if has_ckd and random.random() < 0.5 else _weighted_choice(DEPARTMENTS)
    facility_capability = random.choices(
        ["FULL_RESOURCES", "LIMITED_RESOURCES"], weights=[0.6, 0.4]
    )[0]

    hypertension_class, sbp_range, dbp_range = _weighted_choice(
        [((cls, sbp_r, dbp_r), weight) for cls, sbp_r, dbp_r, weight in HYPERTENSION_BUCKETS]
    )
    sbp = random.randint(*sbp_range)
    dbp = random.randint(*dbp_range)

    is_high_risk = (
        hypertension_class == "GRADE_2_HYPERTENSION"
        or bool(comorbidities)
        or risk_factor_count >= 4
    )
    risk_level = (
        "HIGH"
        if is_high_risk
        else (
            "MEDIUM"
            if risk_factor_count >= 2 or hypertension_class == "GRADE_1_HYPERTENSION"
            else "LOW"
        )
    )
    target_sbp = 130 if (comorbidities or risk_level == "HIGH") else 140
    target_dbp = 80

    patient = PatientRecord(
        fhir_id=f"{prefix}-{index:04d}",
        gender=gender,
        birth_date=birth_date,
        risk_factor_count=risk_factor_count,
        department=department,
        comorbidities=comorbidities,
    )

    visit_date = REFERENCE_DATE - timedelta(days=random.randint(180, 900))
    total_visits = random.randint(4, 6)  # 1 initial + 3-5 follow-ups
    prev_adherent = True
    drugs_by_class: dict[str, tuple[str, str, float]] = {}
    visits_uncontrolled = 0

    for visit_number in range(1, total_visits + 1):
        if visit_number == 1:
            is_early = False
            reason = None
        else:
            early_chance = 0.30 if not prev_adherent else 0.12
            is_early = random.random() < early_chance
            reason = _weighted_choice(EARLY_REVISIT_REASONS) if is_early else None

        bp_controlled = sbp < target_sbp and dbp < target_dbp
        visits_uncontrolled = 0 if bp_controlled else visits_uncontrolled + 1
        current_hypertension_class = hypertension_class if visit_number == 1 else None

        adherent = True if bp_controlled else random.random() < adherence_rate
        if bp_controlled:
            # Already at target: maintain whatever regimen got them there, never
            # escalate or drop drugs just because "recommended" briefly reads empty.
            recommended_classes: list[str] = list(drugs_by_class.keys())
        else:
            recommended_classes = _target_classes(
                hypertension_class, facility_capability, visits_uncontrolled
            )
            if adherent:
                for drug_class in recommended_classes:
                    if drug_class not in drugs_by_class and medicines_by_class.get(drug_class):
                        drug_id, name = random.choice(medicines_by_class[drug_class])
                        low, high = _DOSE_RANGE_MG[drug_class]
                        drugs_by_class[drug_class] = (
                            drug_id,
                            name,
                            round(random.uniform(low, high), 1),
                        )
            # else: clinician doesn't escalate -- regimen (drugs_by_class) stays as-is
        recommended_text = _recommended_action_text(
            recommended_classes,
            bp_controlled=bp_controlled,
            has_active_regimen=bool(drugs_by_class),
        )

        egfr_baseline = random.uniform(25, 55) if has_ckd else random.uniform(70, 110)
        egfr = round(_clamp(egfr_baseline + random.uniform(-4, 4), 10, 130), 1)
        potassium_baseline = (
            random.uniform(4.0, 5.2) if "A" in drugs_by_class else random.uniform(3.8, 4.6)
        )
        potassium = round(_clamp(potassium_baseline + random.uniform(-0.15, 0.15), 3.0, 6.5), 2)

        scheduled_gap_days = (
            180 if bp_controlled else (28 if hypertension_class == "GRADE_2_HYPERTENSION" else 56)
        )
        scheduled_next = visit_date + timedelta(days=scheduled_gap_days)

        patient.visits.append(
            VisitRecord(
                visit_number=visit_number,
                visit_date=visit_date,
                is_early_revisit=is_early,
                early_revisit_reason=reason,
                facility_capability=facility_capability,
                clinic_sbp=sbp,
                clinic_dbp=dbp,
                egfr=egfr,
                potassium=potassium,
                bp_target_sbp=target_sbp,
                bp_target_dbp=target_dbp,
                bp_controlled=bp_controlled,
                hypertension_class=current_hypertension_class,
                risk_level=risk_level,
                cdss_recommended_action=recommended_text,
                actual_drugs=list(drugs_by_class.values()),
                adherent_to_cdss=adherent,
                scheduled_next_visit_date=scheduled_next,
            )
        )

        # Evolve BP toward (adherent) or away from (non-adherent) target for the next visit.
        if adherent and not bp_controlled:
            sbp -= random.randint(5, 20)
            dbp -= random.randint(3, 12)
        elif not adherent and not bp_controlled:
            sbp += random.randint(-5, 10)
            dbp += random.randint(-3, 6)
        else:
            sbp += random.randint(-3, 3)
            dbp += random.randint(-2, 2)
        sbp = int(_clamp(sbp, 100, 200))
        dbp = int(_clamp(dbp, 65, 120))

        # Next visit date: early revisit pulls the date in; routine follow-up drifts near schedule.
        if visit_number < total_visits:
            next_visit_date = patient.visits[-1].scheduled_next_visit_date
            if random.random() < (0.30 if not adherent else 0.12):
                next_visit_date -= timedelta(days=random.randint(7, 30))
            else:
                next_visit_date += timedelta(days=random.randint(-3, 14))
            visit_date = next_visit_date

        prev_adherent = adherent

    return patient


def _patient_to_resources(patient: PatientRecord) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = [
        {
            "resourceType": "Patient",
            "id": patient.fhir_id,
            "gender": patient.gender,
            "birthDate": patient.birth_date.isoformat(),
            "extension": [
                {"url": f"{EXT_BASE}/risk-factor-count", "valueInteger": patient.risk_factor_count},
                {"url": f"{AI4LIFE_BASE}/department", "valueString": patient.department},
            ],
        }
    ]

    icd10, snomed, text = HYPERTENSION_ICD10
    resources.append(
        {
            "resourceType": "Condition",
            "id": f"{patient.fhir_id}-cond-htn",
            "subject": {"reference": f"Patient/{patient.fhir_id}"},
            "code": {
                "coding": [
                    {"system": CS_ICD10, "code": icd10},
                    {"system": CS_SNOMED, "code": snomed},
                ],
                "text": text,
            },
        }
    )
    for code in patient.comorbidities:
        icd10, snomed, text = COMORBIDITIES[code]
        resources.append(
            {
                "resourceType": "Condition",
                "id": f"{patient.fhir_id}-cond-{code.lower()}",
                "subject": {"reference": f"Patient/{patient.fhir_id}"},
                "code": {
                    "coding": [
                        {"system": CS_ICD10, "code": icd10},
                        {"system": CS_SNOMED, "code": snomed},
                    ],
                    "text": text,
                },
            }
        )

    for visit in patient.visits:
        encounter_id = f"{patient.fhir_id}-enc-{visit.visit_number}"
        extensions = [
            {"url": f"{EXT_BASE}/visit-number", "valueInteger": visit.visit_number},
            {"url": f"{EXT_BASE}/is-early-revisit", "valueBoolean": visit.is_early_revisit},
            {"url": f"{EXT_BASE}/facility-capability", "valueString": visit.facility_capability},
            {
                "url": f"{EXT_BASE}/scheduled-next-visit-date",
                "valueDate": visit.scheduled_next_visit_date.isoformat(),
            },
            {"url": f"{EXT_BASE}/risk-level", "valueString": visit.risk_level},
            {"url": f"{EXT_BASE}/bp-target-sbp", "valueInteger": visit.bp_target_sbp},
            {"url": f"{EXT_BASE}/bp-target-dbp", "valueInteger": visit.bp_target_dbp},
            {
                "url": f"{EXT_BASE}/cdss-recommended-action",
                "valueString": visit.cdss_recommended_action,
            },
            {"url": f"{AI4LIFE_BASE}/cdss-adherent", "valueBoolean": visit.adherent_to_cdss},
        ]
        if visit.early_revisit_reason:
            extensions.append(
                {
                    "url": f"{EXT_BASE}/early-revisit-reason",
                    "valueString": visit.early_revisit_reason,
                }
            )
        if visit.hypertension_class:
            extensions.append(
                {"url": f"{EXT_BASE}/hypertension-class", "valueString": visit.hypertension_class}
            )

        resources.append(
            {
                "resourceType": "Encounter",
                "id": encounter_id,
                "status": "finished",
                "class": {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "AMB",
                    "display": "ambulatory",
                },
                "subject": {"reference": f"Patient/{patient.fhir_id}"},
                "period": {"start": visit.visit_date.isoformat()},
                "extension": extensions,
            }
        )

        subject_ref = {"reference": f"Patient/{patient.fhir_id}"}
        encounter_ref = {"reference": f"Encounter/{encounter_id}"}
        resources.append(
            {
                "resourceType": "Observation",
                "id": f"{encounter_id}-obs-sbp",
                "status": "final",
                "code": {
                    "coding": [
                        {
                            "system": SYS_LOINC,
                            "code": "8459-0",
                            "display": "Huyết áp tâm thu (ngồi)",
                        }
                    ]
                },
                "subject": subject_ref,
                "encounter": encounter_ref,
                "valueQuantity": {
                    "value": visit.clinic_sbp,
                    "unit": "mmHg",
                    "system": SYS_UCUM,
                    "code": "mm[Hg]",
                },
            }
        )
        resources.append(
            {
                "resourceType": "Observation",
                "id": f"{encounter_id}-obs-dbp",
                "status": "final",
                "code": {
                    "coding": [
                        {"system": SYS_LOINC, "code": "8462-4", "display": "Huyết áp tâm trương"}
                    ]
                },
                "subject": subject_ref,
                "encounter": encounter_ref,
                "valueQuantity": {
                    "value": visit.clinic_dbp,
                    "unit": "mmHg",
                    "system": SYS_UCUM,
                    "code": "mm[Hg]",
                },
            }
        )
        resources.append(
            {
                "resourceType": "Observation",
                "id": f"{encounter_id}-obs-egfr",
                "status": "final",
                "code": {"coding": [{"system": SYS_LOINC, "code": "98979-8", "display": "eGFR"}]},
                "subject": subject_ref,
                "encounter": encounter_ref,
                "valueQuantity": {
                    "value": visit.egfr,
                    "unit": "mL/min",
                    "system": SYS_UCUM,
                    "code": "mL/min",
                },
            }
        )
        resources.append(
            {
                "resourceType": "Observation",
                "id": f"{encounter_id}-obs-k",
                "status": "final",
                "code": {
                    "coding": [{"system": SYS_LOINC, "code": "6298-4", "display": "Kali (K+)"}]
                },
                "subject": subject_ref,
                "encounter": encounter_ref,
                "valueQuantity": {
                    "value": visit.potassium,
                    "unit": "mmol/L",
                    "system": SYS_UCUM,
                    "code": "mmol/L",
                },
            }
        )
        for drug_id, name, dose_mg in visit.actual_drugs:
            resources.append(
                {
                    "resourceType": "MedicationRequest",
                    "id": f"{encounter_id}-med-{drug_id.lower()}",
                    "status": "active",
                    "intent": "order",
                    "medicationCodeableConcept": {"text": name.upper()},
                    "subject": subject_ref,
                    "encounter": encounter_ref,
                    "authoredOn": visit.visit_date.isoformat(),
                    "dosageInstruction": [
                        {
                            "doseAndRate": [
                                {
                                    "doseQuantity": {
                                        "value": dose_mg,
                                        "unit": "mg",
                                        "system": SYS_UCUM,
                                        "code": "mg",
                                    }
                                }
                            ]
                        }
                    ],
                }
            )

    return resources


def _build_bundle(
    count: int,
    prefix: str,
    seed: int,
    adherence_rate: float,
    medicines_by_class: dict[str, list[tuple[str, str]]],
) -> dict[str, Any]:
    random.seed(seed)
    entries = []
    for i in range(1, count + 1):
        patient = _generate_patient(i, prefix, adherence_rate, medicines_by_class)
        entries.extend(
            {"fullUrl": f"{resource['resourceType']}/{resource['id']}", "resource": resource}
            for resource in _patient_to_resources(patient)
        )
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "fhir"
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    medicines_by_class = _load_medicines_by_class()

    preset_bundle = _build_bundle(
        count=20,
        prefix="preset",
        seed=1,
        adherence_rate=0.78,
        medicines_by_class=medicines_by_class,
    )
    (args.out_dir / "preset_patients.json").write_text(
        json.dumps(preset_bundle, indent=2), encoding="utf-8"
    )

    synthetic_bundle = _build_bundle(
        count=1000,
        prefix="synthetic",
        seed=42,
        adherence_rate=0.78,
        medicines_by_class=medicines_by_class,
    )
    (args.out_dir / "synthetic_patients.json").write_text(
        json.dumps(synthetic_bundle), encoding="utf-8"
    )

    preset_path = args.out_dir / "preset_patients.json"
    synthetic_path = args.out_dir / "synthetic_patients.json"
    print(f"Wrote {len(preset_bundle['entry'])} entries to {preset_path}")
    print(f"Wrote {len(synthetic_bundle['entry'])} entries to {synthetic_path}")


if __name__ == "__main__":
    main()
