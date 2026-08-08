"""Dashboard summary endpoint orchestration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from cdss.api.dependencies import get_dashboard_repository
from cdss.api.routes.dashboard_common import DashboardFilters, dashboard_today
from cdss.api.routes.dashboard_metrics import _build_outcomes, _build_overview, _build_visits
from cdss.api.routes.dashboard_status import _build_fhir_import_status, _build_needs_attention
from cdss.api.routes.dashboard_usage import _build_cdss_usage, _build_efficacy
from cdss.api.schemas.dashboard import DashboardSummaryResponse
from cdss.infrastructure.db.dashboard.dashboard_repository import DashboardRepository

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    department: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    gender: str | None = Query(default=None),
    comorbidity_icd10: str | None = Query(default=None),
    adherent_to_cdss: bool | None = Query(default=None),
) -> DashboardSummaryResponse:
    today = dashboard_today()
    filters = DashboardFilters(
        department, min_age, max_age, gender, comorbidity_icd10, adherent_to_cdss
    )
    patients = repository.list_patients(**filters.as_kwargs())

    return DashboardSummaryResponse(
        overview=_build_overview(repository, today, filters),
        visits=_build_visits(patients, today),
        outcomes=_build_outcomes(repository, today, filters),
        cdss_usage=_build_cdss_usage(repository, patients),
        efficacy=_build_efficacy(patients),
        fhir_import_status=_build_fhir_import_status(repository, patients),
        needs_attention=_build_needs_attention(patients, today, limit=100),
    )
