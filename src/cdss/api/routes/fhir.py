"""FHIR knowledge-base and clinical-data endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_dashboard_repository, get_tree_graph_repository
from cdss.api.routes.fhir_export import build_clinical_bundle
from cdss.api.schemas import EvaluationErrorResponse
from cdss.api.schemas import fhir_clinical as clinical_schemas
from cdss.api.schemas.fhir import Bundle, Library, PlanDefinition
from cdss.api.schemas.fhir_clinical import ImportResult
from cdss.core.database import get_db
from cdss.domain.decision_tree import TreeGraphRepository
from cdss.infrastructure.db.clinical_import import import_bundle
from cdss.infrastructure.db.dashboard.dashboard_repository import DashboardRepository

router = APIRouter(prefix="/fhir", tags=["fhir"])


@router.get("/PlanDefinition", response_model=Bundle, response_model_exclude_none=True)
def list_plan_definitions(
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> Bundle:
    definitions = [
        PlanDefinition.from_graph(repository.get_tree(tree.tree_key))
        for tree in repository.list_trees()
    ]
    return Bundle.from_plan_definitions(definitions)


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
    return PlanDefinition.from_graph(repository.get_tree(tree_key))


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
    library = Library.from_graph(repository.get_tree(tree_key))
    if library is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"tree '{tree_key}' has no GLOBAL nodes",
        )
    return library


@router.post("/import", response_model=ImportResult)
def import_fhir_bundle(
    bundle: dict[str, Any],
    session: Annotated[Session, Depends(get_db)],
    source_label: str = Query(default="manual-import"),
) -> ImportResult:
    return import_bundle(session, bundle, source_label=source_label)


@router.get("/Patient", response_model=clinical_schemas.Bundle, response_model_exclude_none=True)
def export_patients(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    facility_capability: str | None = Query(default=None),
    comorbidity_icd10: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> clinical_schemas.Bundle:
    patients = repository.list_patients(
        facility_capability=facility_capability,
        comorbidity_icd10=comorbidity_icd10,
    )
    return build_clinical_bundle(patients[:limit])


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
    patient = repository.get_patient_by_fhir_id(fhir_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"patient '{fhir_id}' not found")
    return build_clinical_bundle([patient])
