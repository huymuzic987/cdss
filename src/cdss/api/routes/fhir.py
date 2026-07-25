"""HL7 FHIR R4 I/O.

Read-only export of the decision-tree knowledge base (PlanDefinition/Library,
below) plus clinical data I/O for the statistics dashboard: importing
Patient/Condition/Encounter/Observation/MedicationRequest bundles and
exporting them back out (see ``fhir_clinical.py`` for those resource shapes).
"""

from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_dashboard_repository, get_tree_graph_repository
from cdss.api.schemas import EvaluationErrorResponse
from cdss.api.schemas import fhir_clinical as clinical_schemas
from cdss.api.schemas.fhir import Bundle, Library, PlanDefinition
from cdss.api.schemas.fhir_clinical import ImportResult
from cdss.core.database import get_db
from cdss.domain.decision_tree import TreeGraphRepository
from cdss.infrastructure.db.clinical_import import import_bundle
from cdss.infrastructure.db.dashboard_repository import DashboardRepository
from cdss.infrastructure.db.models import Patient as PatientRow

router = APIRouter(prefix="/fhir", tags=["fhir"])


@router.get("/PlanDefinition", response_model=Bundle, response_model_exclude_none=True)
def list_plan_definitions(
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> Bundle:
    plan_definitions = [
        PlanDefinition.from_graph(repository.get_tree(tree.tree_key))
        for tree in repository.list_trees()
    ]
    return Bundle.from_plan_definitions(plan_definitions)


@router.get(
    "/PlanDefinition/{tree_key}",
    response_model=PlanDefinition,
    response_model_exclude_none=True,
    responses={404: {"model": EvaluationErrorResponse}},
)
def get_plan_definition(
    tree_key: str,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> PlanDefinition:
    graph = repository.get_tree(tree_key)
    return PlanDefinition.from_graph(graph)


@router.get(
    "/Library/{tree_key}",
    response_model=Library,
    response_model_exclude_none=True,
    responses={404: {"model": EvaluationErrorResponse}},
)
def get_library(
    tree_key: str,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> Library:
    graph = repository.get_tree(tree_key)
    library = Library.from_graph(graph)
    if library is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"tree '{tree_key}' has no GLOBAL nodes",
        )
    return library


# --- Clinical data (patients/visits) import & export ---------------------------


@router.post("/import", response_model=ImportResult)
def import_fhir_bundle(
    bundle: dict[str, Any],
    session: Annotated[Session, Depends(get_db)],
    source_label: str = Query(default="manual-import"),
) -> ImportResult:
    """Import a FHIR R4 Bundle of Patient/Condition/Encounter/Observation/
    MedicationRequest resources, upserting into patients/visits."""
    return import_bundle(session, bundle, source_label=source_label)


def _build_clinical_bundle(patients: Sequence[PatientRow]) -> clinical_schemas.Bundle:
    entries: list[clinical_schemas.BundleEntry] = []
    for patient in patients:
        fhir_patient = clinical_schemas.Patient.from_row(
            fhir_id=patient.fhir_id,
            gender=patient.gender,
            birth_date=patient.birth_date.isoformat() if patient.birth_date else None,
            risk_factor_count=patient.risk_factor_count,
            department=patient.department,
        )
        entries.append(
            clinical_schemas.BundleEntry(
                fullUrl=f"Patient/{patient.fhir_id}",
                resource=fhir_patient.model_dump(by_alias=True, exclude_none=True),
            )
        )
        for condition_row in patient.conditions:
            condition = clinical_schemas.Condition.from_row(
                condition_id=condition_row.fhir_condition_id,
                patient_fhir_id=patient.fhir_id,
                icd10_code=condition_row.icd10_code,
                snomed_code=condition_row.snomed_code,
                condition_text=condition_row.condition_text,
            )
            entries.append(
                clinical_schemas.BundleEntry(
                    fullUrl=f"Condition/{condition.id}",
                    resource=condition.model_dump(by_alias=True, exclude_none=True),
                )
            )
        for visit in sorted(patient.visits, key=lambda v: v.visit_number):
            encounter_id = visit.fhir_encounter_id
            encounter = clinical_schemas.Encounter.from_visit(
                encounter_id=encounter_id,
                patient_fhir_id=patient.fhir_id,
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
            entries.append(
                clinical_schemas.BundleEntry(
                    fullUrl=f"Encounter/{encounter_id}",
                    resource=encounter.model_dump(by_alias=True, exclude_none=True),
                )
            )
            if visit.clinic_sbp is not None and visit.clinic_dbp is not None:
                for obs in clinical_schemas.Observation.blood_pressure_pair(
                    observation_id_prefix=encounter_id,
                    patient_fhir_id=patient.fhir_id,
                    encounter_id=encounter_id,
                    sbp=visit.clinic_sbp,
                    dbp=visit.clinic_dbp,
                ):
                    entries.append(
                        clinical_schemas.BundleEntry(
                            fullUrl=f"Observation/{obs.id}",
                            resource=obs.model_dump(by_alias=True, exclude_none=True),
                        )
                    )
            for observation_row in visit.observations:
                obs = clinical_schemas.Observation.from_reading(
                    observation_id=f"{encounter_id}-obs-{observation_row.id}",
                    patient_fhir_id=patient.fhir_id,
                    encounter_id=encounter_id,
                    loinc_code=observation_row.loinc_code,
                    display=observation_row.display_name,
                    value=observation_row.value,
                    unit=observation_row.unit or "",
                )
                entries.append(
                    clinical_schemas.BundleEntry(
                        fullUrl=f"Observation/{obs.id}",
                        resource=obs.model_dump(by_alias=True, exclude_none=True),
                    )
                )
            for medication_row in visit.medications:
                med = clinical_schemas.MedicationRequest.from_row(
                    request_id=f"{encounter_id}-med-{medication_row.id}",
                    patient_fhir_id=patient.fhir_id,
                    encounter_id=encounter_id,
                    drug_name=medication_row.drug_name,
                    drug_class_note=medication_row.drug_class_note,
                    dose_value=medication_row.dose_value,
                    dose_unit=medication_row.dose_unit,
                    authored_on=visit.visit_date.isoformat(),
                )
                entries.append(
                    clinical_schemas.BundleEntry(
                        fullUrl=f"MedicationRequest/{med.id}",
                        resource=med.model_dump(by_alias=True, exclude_none=True),
                    )
                )
    return clinical_schemas.Bundle(type="searchset", entry=entries)


@router.get("/Patient", response_model=clinical_schemas.Bundle, response_model_exclude_none=True)
def export_patients(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    facility_capability: str | None = Query(default=None),
    comorbidity_icd10: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> clinical_schemas.Bundle:
    """Export a (optionally filtered) cohort of patients as a FHIR Bundle."""
    patients = repository.list_patients(
        facility_capability=facility_capability, comorbidity_icd10=comorbidity_icd10
    )
    return _build_clinical_bundle(patients[:limit])


@router.get(
    "/Patient/{fhir_id}",
    response_model=clinical_schemas.Bundle,
    response_model_exclude_none=True,
    responses={404: {"model": EvaluationErrorResponse}},
)
def export_patient(
    fhir_id: str,
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
) -> clinical_schemas.Bundle:
    """Export one patient's full record (Patient + Conditions + Encounters +
    Observations + MedicationRequests) as a FHIR Bundle."""
    matches = [p for p in repository.list_patients() if p.fhir_id == fhir_id]
    if not matches:
        raise HTTPException(status_code=404, detail=f"patient '{fhir_id}' not found")
    return _build_clinical_bundle(matches)
