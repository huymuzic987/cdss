"""Import a FHIR R4 Bundle (Patient/Condition/Encounter/Observation/
MedicationRequest) into the patients/patient_conditions/visits/
visit_observations/visit_medications tables.

Parsing is intentionally defensive dict access rather than strict pydantic
validation: real-world FHIR bundles vary in shape, and a single malformed
resource should not abort an entire 1000-patient import. Each resource that
fails to parse is recorded in ``ImportResult.errors`` and skipped.

Two encounter shapes are supported:
  - Longitudinal: one or more FHIR ``Encounter`` resources per patient, each
    with Observations/MedicationRequests referencing it via `encounter`.
  - Single-snapshot (the project's real reference data under
    `backups/test_case/`): no `Encounter` resource at all, Observations and
    MedicationRequests reference only `subject`. These import as an implicit
    visit_number=1, dated from the earliest Observation.effectiveDateTime
    (falling back to Bundle.timestamp).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cdss.api.schemas.fhir_clinical import (
    EXT_ADHERENT_TO_CDSS,
    EXT_BASE,
    EXT_DEPARTMENT,
    LOINC_DBP_CODE,
    LOINC_SBP_CODE,
    SYS_ICD10,
    SYS_SNOMED,
    ImportResult,
)
from cdss.infrastructure.db.models import (
    FhirImportBatch,
    Medicine,
    Patient,
    PatientCondition,
    Visit,
    VisitMedication,
    VisitObservation,
)


def _ext_value(extensions: list[dict[str, Any]], url: str) -> Any:
    for ext in extensions:
        if ext.get("url") != url:
            continue
        for key in ("valueString", "valueInteger", "valueBoolean", "valueDate"):
            if key in ext:
                return ext[key]
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _reference_id(reference: str | None) -> str | None:
    if not reference or "/" not in reference:
        return None
    return reference.split("/", 1)[1]


def _drug_class_note(medication_request: dict[str, Any]) -> str | None:
    for note in medication_request.get("note") or []:
        text = note.get("text", "")
        if text.startswith("drugClass:"):
            return text.split(":", 1)[1].strip()
    return None


def _dose(medication_request: dict[str, Any]) -> tuple[float | None, str | None]:
    dosage = medication_request.get("dosageInstruction") or []
    if not dosage:
        return None, None
    dose_and_rate = dosage[0].get("doseAndRate") or []
    if not dose_and_rate:
        return None, None
    quantity = dose_and_rate[0].get("doseQuantity") or {}
    return quantity.get("value"), quantity.get("unit")


def import_bundle(session: Session, bundle: dict[str, Any], source_label: str) -> ImportResult:
    entries = bundle.get("entry") or []
    resources_by_type: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        resource = entry.get("resource") or {}
        resource_type = resource.get("resourceType")
        if not resource_type:
            continue
        resources_by_type.setdefault(resource_type, []).append(resource)

    errors: list[dict[str, str]] = []

    existing_patients = {p.fhir_id: p for p in session.execute(select(Patient)).scalars()}
    existing_visits = {v.fhir_encounter_id: v for v in session.execute(select(Visit)).scalars()}
    medicine_by_name = {
        name.strip().lower(): drug_id
        for drug_id, name in session.execute(select(Medicine.drug_id, Medicine.name)).all()
    }

    # ---- Patients ----
    patient_row_by_fhir_id: dict[str, Patient] = {}
    patient_resource_by_fhir_id: dict[str, dict[str, Any]] = {}
    patients_imported = 0
    for resource in resources_by_type.get("Patient", []):
        fhir_id = resource.get("id")
        if not fhir_id:
            errors.append({"resource": "Patient", "message": "missing id"})
            continue
        extensions = resource.get("extension") or []
        risk_factor_count = _ext_value(extensions, f"{EXT_BASE}/risk-factor-count") or 0

        patient = existing_patients.get(fhir_id)
        if patient is None:
            patient = Patient(id=uuid.uuid4(), fhir_id=fhir_id)
            session.add(patient)
            existing_patients[fhir_id] = patient
        patient.gender = resource.get("gender")
        patient.birth_date = _parse_date(resource.get("birthDate"))
        patient.risk_factor_count = int(risk_factor_count)
        patient.department = _ext_value(extensions, EXT_DEPARTMENT)

        patient_row_by_fhir_id[fhir_id] = patient
        patient_resource_by_fhir_id[fhir_id] = resource
        patients_imported += 1

    # ---- Conditions -> replace each patient's condition set ----
    conditions_by_patient: dict[str, list[dict[str, Any]]] = {}
    for condition in resources_by_type.get("Condition", []):
        patient_fhir_id = _reference_id((condition.get("subject") or {}).get("reference"))
        if not patient_fhir_id:
            errors.append({"resource": "Condition", "message": "missing subject"})
            continue
        conditions_by_patient.setdefault(patient_fhir_id, []).append(condition)

    for patient_fhir_id, conditions in conditions_by_patient.items():
        patient = patient_row_by_fhir_id.get(patient_fhir_id)
        if patient is None:
            errors.append(
                {
                    "resource": "Condition",
                    "message": f"references unknown patient {patient_fhir_id}",
                }
            )
            continue
        session.execute(delete(PatientCondition).where(PatientCondition.patient_id == patient.id))
        for condition in conditions:
            fhir_condition_id = condition.get("id")
            if not fhir_condition_id:
                errors.append({"resource": "Condition", "message": "missing id"})
                continue
            codings = (condition.get("code") or {}).get("coding") or []
            icd10_code = next(
                (c.get("code") for c in codings if c.get("system") == SYS_ICD10), None
            )
            snomed_code = next(
                (c.get("code") for c in codings if c.get("system") == SYS_SNOMED), None
            )
            session.add(
                PatientCondition(
                    id=uuid.uuid4(),
                    patient_id=patient.id,
                    fhir_condition_id=fhir_condition_id,
                    icd10_code=icd10_code,
                    snomed_code=snomed_code,
                    condition_text=(condition.get("code") or {}).get("text"),
                )
            )

    # ---- Observations & MedicationRequests, grouped by encounter (or by
    # patient when the resource carries no `encounter` reference at all) ----
    observations_by_encounter: dict[str, list[dict[str, Any]]] = {}
    observations_by_patient: dict[str, list[dict[str, Any]]] = {}
    for observation in resources_by_type.get("Observation", []):
        encounter_id = _reference_id((observation.get("encounter") or {}).get("reference"))
        if encounter_id:
            observations_by_encounter.setdefault(encounter_id, []).append(observation)
            continue
        patient_fhir_id = _reference_id((observation.get("subject") or {}).get("reference"))
        if not patient_fhir_id:
            errors.append({"resource": "Observation", "message": "missing subject and encounter"})
            continue
        observations_by_patient.setdefault(patient_fhir_id, []).append(observation)

    medications_by_encounter: dict[str, list[dict[str, Any]]] = {}
    medications_by_patient: dict[str, list[dict[str, Any]]] = {}
    for med_request in resources_by_type.get("MedicationRequest", []):
        encounter_id = _reference_id((med_request.get("encounter") or {}).get("reference"))
        if encounter_id:
            medications_by_encounter.setdefault(encounter_id, []).append(med_request)
            continue
        patient_fhir_id = _reference_id((med_request.get("subject") or {}).get("reference"))
        if not patient_fhir_id:
            errors.append(
                {"resource": "MedicationRequest", "message": "missing subject and encounter"}
            )
            continue
        medications_by_patient.setdefault(patient_fhir_id, []).append(med_request)

    def _apply_observations(visit: Visit, observations: list[dict[str, Any]]) -> None:
        session.execute(delete(VisitObservation).where(VisitObservation.visit_id == visit.id))
        for observation in observations:
            codings = (observation.get("code") or {}).get("coding") or []
            code = codings[0].get("code") if codings else None
            display = codings[0].get("display") if codings else None
            value = (observation.get("valueQuantity") or {}).get("value")
            unit = (observation.get("valueQuantity") or {}).get("unit")
            if code is None or value is None:
                errors.append({"resource": "Observation", "message": "missing code or value"})
                continue
            if code == LOINC_SBP_CODE:
                visit.clinic_sbp = int(value)
            elif code == LOINC_DBP_CODE:
                visit.clinic_dbp = int(value)
            else:
                session.add(
                    VisitObservation(
                        id=uuid.uuid4(),
                        visit_id=visit.id,
                        loinc_code=code,
                        display_name=display,
                        value=float(value),
                        unit=unit,
                    )
                )
        if (
            visit.clinic_sbp is not None
            and visit.clinic_dbp is not None
            and visit.bp_target_sbp
            and visit.bp_target_dbp
        ):
            visit.bp_controlled = (
                visit.clinic_sbp < visit.bp_target_sbp and visit.clinic_dbp < visit.bp_target_dbp
            )

    def _apply_medications(visit: Visit, medications: list[dict[str, Any]]) -> None:
        session.execute(delete(VisitMedication).where(VisitMedication.visit_id == visit.id))
        for med_request in medications:
            drug_name = (med_request.get("medicationCodeableConcept") or {}).get("text")
            if not drug_name:
                errors.append(
                    {"resource": "MedicationRequest", "message": "missing medication text"}
                )
                continue
            dose_value, dose_unit = _dose(med_request)
            session.add(
                VisitMedication(
                    id=uuid.uuid4(),
                    visit_id=visit.id,
                    drug_id=medicine_by_name.get(drug_name.strip().lower()),
                    drug_name=drug_name,
                    drug_class_note=_drug_class_note(med_request),
                    dose_value=dose_value,
                    dose_unit=dose_unit,
                )
            )

    def _upsert_visit(fhir_encounter_id: str, patient: Patient, **fields: Any) -> Visit:
        visit = existing_visits.get(fhir_encounter_id)
        if visit is None:
            visit = Visit(
                id=uuid.uuid4(), patient_id=patient.id, fhir_encounter_id=fhir_encounter_id
            )
            session.add(visit)
            existing_visits[fhir_encounter_id] = visit
        visit.patient_id = patient.id
        for key, value in fields.items():
            setattr(visit, key, value)
        return visit

    # ---- Encounters -> visits (explicit, longitudinal bundles) ----
    encounters = resources_by_type.get("Encounter", [])
    visits_imported = 0
    for resource in encounters:
        fhir_encounter_id = resource.get("id")
        patient_fhir_id = _reference_id((resource.get("subject") or {}).get("reference"))
        visit_date = _parse_date((resource.get("period") or {}).get("start"))
        if not fhir_encounter_id or not patient_fhir_id or visit_date is None:
            errors.append(
                {"resource": "Encounter", "message": "missing id, subject, or period.start"}
            )
            continue
        patient = patient_row_by_fhir_id.get(patient_fhir_id)
        if patient is None:
            errors.append(
                {
                    "resource": "Encounter",
                    "message": f"references unknown patient {patient_fhir_id}",
                }
            )
            continue

        extensions = resource.get("extension") or []
        visit_number = _ext_value(extensions, f"{EXT_BASE}/visit-number")
        if visit_number is None:
            errors.append({"resource": "Encounter", "message": "missing visit-number extension"})
            continue

        visit = _upsert_visit(
            fhir_encounter_id,
            patient,
            visit_number=int(visit_number),
            visit_date=visit_date,
            facility_capability=_ext_value(extensions, f"{EXT_BASE}/facility-capability"),
            is_early_revisit=bool(_ext_value(extensions, f"{EXT_BASE}/is-early-revisit") or False),
            early_revisit_reason=_ext_value(extensions, f"{EXT_BASE}/early-revisit-reason"),
            scheduled_next_visit_date=_parse_date(
                _ext_value(extensions, f"{EXT_BASE}/scheduled-next-visit-date")
            ),
            hypertension_class=_ext_value(extensions, f"{EXT_BASE}/hypertension-class"),
            risk_level=_ext_value(extensions, f"{EXT_BASE}/risk-level"),
            bp_target_sbp=_ext_value(extensions, f"{EXT_BASE}/bp-target-sbp"),
            bp_target_dbp=_ext_value(extensions, f"{EXT_BASE}/bp-target-dbp"),
            cdss_recommended_action=_ext_value(extensions, f"{EXT_BASE}/cdss-recommended-action"),
            adherent_to_cdss=_ext_value(extensions, EXT_ADHERENT_TO_CDSS),
        )
        _apply_observations(visit, observations_by_encounter.get(fhir_encounter_id, []))
        _apply_medications(visit, medications_by_encounter.get(fhir_encounter_id, []))
        visits_imported += 1

    # ---- Single-snapshot bundles (no Encounter at all): one implicit visit ----
    if not encounters:
        for patient_fhir_id, patient in patient_row_by_fhir_id.items():
            patient_observations = observations_by_patient.get(patient_fhir_id, [])
            candidate_dates = sorted(
                d for o in patient_observations if (d := o.get("effectiveDateTime"))
            )
            visit_date = _parse_date(
                candidate_dates[0] if candidate_dates else bundle.get("timestamp")
            )
            if visit_date is None:
                errors.append(
                    {
                        "resource": "Patient",
                        "message": f"cannot derive an implicit visit date for {patient_fhir_id}",
                    }
                )
                continue

            patient_extensions = (
                patient_resource_by_fhir_id.get(patient_fhir_id, {}).get("extension") or []
            )
            visit = _upsert_visit(
                f"{patient_fhir_id}-implicit-visit-1",
                patient,
                visit_number=1,
                visit_date=visit_date,
                adherent_to_cdss=_ext_value(patient_extensions, EXT_ADHERENT_TO_CDSS),
            )
            _apply_observations(visit, patient_observations)
            _apply_medications(visit, medications_by_patient.get(patient_fhir_id, []))
            visits_imported += 1

    batch = FhirImportBatch(
        id=uuid.uuid4(),
        source_label=source_label,
        patient_count=patients_imported,
        visit_count=visits_imported,
        error_count=len(errors),
        errors=errors,
    )
    session.add(batch)
    session.commit()

    return ImportResult(
        source_label=source_label,
        patients_imported=patients_imported,
        visits_imported=visits_imported,
        error_count=len(errors),
        errors=errors,
    )
