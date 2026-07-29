"""Serialize persisted clinical records into a FHIR bundle."""

from collections.abc import Sequence
from typing import Any

from cdss.api.schemas import fhir_clinical as schemas
from cdss.infrastructure.db.models import Patient


def build_clinical_bundle(patients: Sequence[Patient]) -> schemas.Bundle:
    entries: list[schemas.BundleEntry] = []
    for patient in patients:
        resource = schemas.Patient.from_row(
            fhir_id=patient.fhir_id,
            gender=patient.gender,
            birth_date=patient.birth_date.isoformat() if patient.birth_date else None,
            risk_factor_count=patient.risk_factor_count,
            department=patient.department,
        )
        _append(entries, f"Patient/{patient.fhir_id}", resource)
        _append_conditions(entries, patient)
        for visit in sorted(patient.visits, key=lambda item: item.visit_number):
            _append_visit(entries, patient.fhir_id, visit)
    return schemas.Bundle(type="searchset", entry=entries)


def _append_conditions(entries: list[schemas.BundleEntry], patient: Patient) -> None:
    for row in patient.conditions:
        resource = schemas.Condition.from_row(
            condition_id=row.fhir_condition_id,
            patient_fhir_id=patient.fhir_id,
            icd10_code=row.icd10_code,
            snomed_code=row.snomed_code,
            condition_text=row.condition_text,
        )
        _append(entries, f"Condition/{resource.id}", resource)


def _append_visit(entries: list[schemas.BundleEntry], patient_id: str, visit: Any) -> None:
    encounter_id = visit.fhir_encounter_id
    resource = schemas.Encounter.from_visit(
        encounter_id=encounter_id,
        patient_fhir_id=patient_id,
        visit={
            "visit_number": visit.visit_number,
            "is_early_revisit": visit.is_early_revisit,
            "facility_capability": visit.facility_capability,
            "early_revisit_reason": visit.early_revisit_reason,
            "scheduled_next_visit_date": (
                visit.scheduled_next_visit_date.isoformat()
                if visit.scheduled_next_visit_date
                else None
            ),
            "hypertension_class": visit.hypertension_class,
            "risk_level": visit.risk_level,
            "bp_target_sbp": visit.bp_target_sbp,
            "bp_target_dbp": visit.bp_target_dbp,
            "cdss_recommended_action": visit.cdss_recommended_action,
            "adherent_to_cdss": visit.adherent_to_cdss,
            "visit_date": visit.visit_date.isoformat(),
        },
    )
    _append(entries, f"Encounter/{encounter_id}", resource)
    _append_observations(entries, patient_id, encounter_id, visit)
    _append_medications(entries, patient_id, encounter_id, visit)


def _append_observations(
    entries: list[schemas.BundleEntry], patient_id: str, encounter_id: str, visit: Any
) -> None:
    if visit.clinic_sbp is not None and visit.clinic_dbp is not None:
        resources = schemas.Observation.blood_pressure_pair(
            observation_id_prefix=encounter_id,
            patient_fhir_id=patient_id,
            encounter_id=encounter_id,
            sbp=visit.clinic_sbp,
            dbp=visit.clinic_dbp,
        )
        for resource in resources:
            _append(entries, f"Observation/{resource.id}", resource)
    for row in visit.observations:
        resource = schemas.Observation.from_reading(
            observation_id=f"{encounter_id}-obs-{row.id}",
            patient_fhir_id=patient_id,
            encounter_id=encounter_id,
            loinc_code=row.loinc_code,
            display=row.display_name,
            value=row.value,
            unit=row.unit or "",
        )
        _append(entries, f"Observation/{resource.id}", resource)


def _append_medications(
    entries: list[schemas.BundleEntry], patient_id: str, encounter_id: str, visit: Any
) -> None:
    for row in visit.medications:
        resource = schemas.MedicationRequest.from_row(
            request_id=f"{encounter_id}-med-{row.id}",
            patient_fhir_id=patient_id,
            encounter_id=encounter_id,
            drug_name=row.drug_name,
            drug_class_note=row.drug_class_note,
            dose_value=row.dose_value,
            dose_unit=row.dose_unit,
            authored_on=visit.visit_date.isoformat(),
        )
        _append(entries, f"MedicationRequest/{resource.id}", resource)


def _append(entries: list[schemas.BundleEntry], url: str, resource: Any) -> None:
    entries.append(
        schemas.BundleEntry(
            fullUrl=url,
            resource=resource.model_dump(by_alias=True, exclude_none=True),
        )
    )
