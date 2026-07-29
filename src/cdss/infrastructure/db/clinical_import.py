"""Transactional coordination of defensive clinical FHIR imports."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from cdss.api.schemas.fhir_clinical import EXT_ADHERENT_TO_CDSS, EXT_BASE, ImportResult
from cdss.infrastructure.db.fhir_import_parsing import extension_value, parse_date, reference_id
from cdss.infrastructure.db.fhir_patient_import import import_patients_and_conditions
from cdss.infrastructure.db.fhir_resource_writer import ClinicalResourceWriter
from cdss.infrastructure.db.models import FhirImportBatch, Medicine, Visit


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

    existing_visits = {v.fhir_encounter_id: v for v in session.execute(select(Visit)).scalars()}
    medicine_by_name = {
        name.strip().lower(): drug_id
        for drug_id, name in session.execute(select(Medicine.drug_id, Medicine.name)).all()
    }
    patient_result = import_patients_and_conditions(session, resources_by_type, errors)
    patient_row_by_fhir_id = patient_result.rows
    patient_resource_by_fhir_id = patient_result.resources
    patients_imported = patient_result.imported_count
    # ---- Observations & MedicationRequests, grouped by encounter (or by
    # patient when the resource carries no `encounter` reference at all) ----
    observations_by_encounter: dict[str, list[dict[str, Any]]] = {}
    observations_by_patient: dict[str, list[dict[str, Any]]] = {}
    for observation in resources_by_type.get("Observation", []):
        encounter_id = reference_id((observation.get("encounter") or {}).get("reference"))
        if encounter_id:
            observations_by_encounter.setdefault(encounter_id, []).append(observation)
            continue
        patient_fhir_id = reference_id((observation.get("subject") or {}).get("reference"))
        if not patient_fhir_id:
            errors.append({"resource": "Observation", "message": "missing subject and encounter"})
            continue
        observations_by_patient.setdefault(patient_fhir_id, []).append(observation)

    medications_by_encounter: dict[str, list[dict[str, Any]]] = {}
    medications_by_patient: dict[str, list[dict[str, Any]]] = {}
    for med_request in resources_by_type.get("MedicationRequest", []):
        encounter_id = reference_id((med_request.get("encounter") or {}).get("reference"))
        if encounter_id:
            medications_by_encounter.setdefault(encounter_id, []).append(med_request)
            continue
        patient_fhir_id = reference_id((med_request.get("subject") or {}).get("reference"))
        if not patient_fhir_id:
            errors.append(
                {"resource": "MedicationRequest", "message": "missing subject and encounter"}
            )
            continue
        medications_by_patient.setdefault(patient_fhir_id, []).append(med_request)

    writer = ClinicalResourceWriter(session, errors, existing_visits, medicine_by_name)
    # ---- Encounters -> visits (explicit, longitudinal bundles) ----
    encounters = resources_by_type.get("Encounter", [])
    visits_imported = 0
    for resource in encounters:
        fhir_encounter_id = resource.get("id")
        patient_fhir_id = reference_id((resource.get("subject") or {}).get("reference"))
        visit_date = parse_date((resource.get("period") or {}).get("start"))
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
        visit_number = extension_value(extensions, f"{EXT_BASE}/visit-number")
        if visit_number is None:
            errors.append({"resource": "Encounter", "message": "missing visit-number extension"})
            continue

        visit = writer.upsert_visit(
            fhir_encounter_id,
            patient,
            visit_number=int(visit_number),
            visit_date=visit_date,
            facility_capability=extension_value(extensions, f"{EXT_BASE}/facility-capability"),
            is_early_revisit=bool(
                extension_value(extensions, f"{EXT_BASE}/is-early-revisit") or False
            ),
            early_revisit_reason=extension_value(extensions, f"{EXT_BASE}/early-revisit-reason"),
            scheduled_next_visit_date=parse_date(
                extension_value(extensions, f"{EXT_BASE}/scheduled-next-visit-date")
            ),
            hypertension_class=extension_value(extensions, f"{EXT_BASE}/hypertension-class"),
            risk_level=extension_value(extensions, f"{EXT_BASE}/risk-level"),
            bp_target_sbp=extension_value(extensions, f"{EXT_BASE}/bp-target-sbp"),
            bp_target_dbp=extension_value(extensions, f"{EXT_BASE}/bp-target-dbp"),
            cdss_recommended_action=extension_value(
                extensions, f"{EXT_BASE}/cdss-recommended-action"
            ),
            adherent_to_cdss=extension_value(extensions, EXT_ADHERENT_TO_CDSS),
        )
        writer.apply_observations(visit, observations_by_encounter.get(fhir_encounter_id, []))
        writer.apply_medications(visit, medications_by_encounter.get(fhir_encounter_id, []))
        visits_imported += 1

    # ---- Single-snapshot bundles (no Encounter at all): one implicit visit ----
    if not encounters:
        for patient_fhir_id, patient in patient_row_by_fhir_id.items():
            patient_observations = observations_by_patient.get(patient_fhir_id, [])
            candidate_dates = sorted(
                d for o in patient_observations if (d := o.get("effectiveDateTime"))
            )
            visit_date = parse_date(
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
            visit = writer.upsert_visit(
                f"{patient_fhir_id}-implicit-visit-1",
                patient,
                visit_number=1,
                visit_date=visit_date,
                adherent_to_cdss=extension_value(patient_extensions, EXT_ADHERENT_TO_CDSS),
            )
            writer.apply_observations(visit, patient_observations)
            writer.apply_medications(visit, medications_by_patient.get(patient_fhir_id, []))
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
