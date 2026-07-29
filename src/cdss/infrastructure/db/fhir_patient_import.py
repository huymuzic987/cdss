"""Patient and condition persistence for clinical FHIR imports."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cdss.api.schemas.fhir_clinical import EXT_BASE, EXT_DEPARTMENT, SYS_ICD10, SYS_SNOMED
from cdss.infrastructure.db.fhir_import_parsing import extension_value, parse_date, reference_id
from cdss.infrastructure.db.models import Patient, PatientCondition


@dataclass(slots=True)
class PatientImportResult:
    rows: dict[str, Patient]
    resources: dict[str, dict[str, Any]]
    imported_count: int


def import_patients_and_conditions(
    session: Session,
    resources_by_type: dict[str, list[dict[str, Any]]],
    errors: list[dict[str, str]],
) -> PatientImportResult:
    existing_patients = {p.fhir_id: p for p in session.execute(select(Patient)).scalars()}
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
        risk_factor_count = extension_value(extensions, f"{EXT_BASE}/risk-factor-count") or 0

        patient = existing_patients.get(fhir_id)
        if patient is None:
            patient = Patient(id=uuid.uuid4(), fhir_id=fhir_id)
            session.add(patient)
            existing_patients[fhir_id] = patient
        patient.gender = resource.get("gender")
        patient.birth_date = parse_date(resource.get("birthDate"))
        patient.risk_factor_count = int(risk_factor_count)
        patient.department = extension_value(extensions, EXT_DEPARTMENT)

        patient_row_by_fhir_id[fhir_id] = patient
        patient_resource_by_fhir_id[fhir_id] = resource
        patients_imported += 1

    # ---- Conditions -> replace each patient's condition set ----
    conditions_by_patient: dict[str, list[dict[str, Any]]] = {}
    for condition in resources_by_type.get("Condition", []):
        patient_fhir_id = reference_id((condition.get("subject") or {}).get("reference"))
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

    return PatientImportResult(
        rows=patient_row_by_fhir_id,
        resources=patient_resource_by_fhir_id,
        imported_count=patients_imported,
    )
