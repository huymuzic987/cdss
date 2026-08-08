"""Dashboard patient search and detail endpoints."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from cdss.api.dependencies import get_dashboard_repository
from cdss.api.routes.dashboard_common import dashboard_today, last_visit
from cdss.api.schemas.dashboard import (
    PatientConditionSummary,
    PatientDetailResponse,
    PatientListItem,
    PatientListResponse,
    PatientVisitDetail,
    VisitMedicationSummary,
    VisitObservationSummary,
)
from cdss.infrastructure.db.dashboard.dashboard_repository import DashboardRepository
from cdss.infrastructure.db.models import Patient

router = APIRouter()


@router.get("/patients", response_model=PatientListResponse)
def search_patients(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    q: str | None = Query(default=None, description="Matches patient ID or department"),
    gender: str | None = Query(default=None),
    status: Literal["overdue", "bp_not_controlled", "early_revisit"] | None = Query(default=None),
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
) -> PatientListResponse:
    """Search/browse patients by ID, department, gender, or clinical status.

    There is no patient name anywhere in the data model -- FHIR imports carry
    only an id, gender, birth date, and department -- so ``q`` matches against
    ``fhir_id``/``department`` rather than a name. Independent of the cohort
    filter bar on the main dashboard.
    """
    today = dashboard_today()

    def _matches(p: Patient) -> bool:
        if gender and (p.gender or "unknown") != gender:
            return False
        if q:
            needle = q.strip().lower()
            haystack = f"{p.fhir_id} {p.department or ''}".lower()
            if needle not in haystack:
                return False
        if status:
            last = last_visit(p)
            if last is None:
                return False
            if status == "overdue" and not (
                last.scheduled_next_visit_date and last.scheduled_next_visit_date < today
            ):
                return False
            if status == "bp_not_controlled" and last.bp_controlled is not False:
                return False
            if status == "early_revisit" and not last.is_early_revisit:
                return False
        return True

    def _sort_key(p: Patient) -> date:
        last = last_visit(p)
        return last.visit_date if last else date.min

    matched = [p for p in repository.list_patients() if _matches(p)]
    matched.sort(key=_sort_key, reverse=True)

    page = matched[offset : offset + limit]
    items = []
    for p in page:
        last = last_visit(p)
        items.append(
            PatientListItem(
                fhir_id=p.fhir_id,
                gender=p.gender,
                birth_date=p.birth_date,
                department=p.department,
                last_visit_date=last.visit_date if last else None,
                visit_count=len(p.visits),
                last_bp_controlled=last.bp_controlled if last else None,
                last_risk_level=last.risk_level if last else None,
                is_overdue=bool(
                    last
                    and last.scheduled_next_visit_date
                    and last.scheduled_next_visit_date < today
                ),
            )
        )
    return PatientListResponse(items=items, total=len(matched))


@router.get("/patients/{fhir_id}", response_model=PatientDetailResponse)
def get_patient_detail(
    fhir_id: str,
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
) -> PatientDetailResponse:
    patient = repository.get_patient_by_fhir_id(fhir_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"patient not found: {fhir_id}")

    return PatientDetailResponse(
        fhir_id=patient.fhir_id,
        gender=patient.gender,
        birth_date=patient.birth_date,
        department=patient.department,
        risk_factor_count=patient.risk_factor_count,
        conditions=[
            PatientConditionSummary(
                icd10_code=c.icd10_code, snomed_code=c.snomed_code, condition_text=c.condition_text
            )
            for c in patient.conditions
        ],
        visits=[
            PatientVisitDetail(
                visit_number=v.visit_number,
                visit_date=v.visit_date,
                facility_capability=v.facility_capability,
                is_early_revisit=v.is_early_revisit,
                early_revisit_reason=v.early_revisit_reason,
                scheduled_next_visit_date=v.scheduled_next_visit_date,
                clinic_sbp=v.clinic_sbp,
                clinic_dbp=v.clinic_dbp,
                bp_target_sbp=v.bp_target_sbp,
                bp_target_dbp=v.bp_target_dbp,
                bp_controlled=v.bp_controlled,
                hypertension_class=v.hypertension_class,
                risk_level=v.risk_level,
                cdss_recommended_action=v.cdss_recommended_action,
                adherent_to_cdss=v.adherent_to_cdss,
                medications=[
                    VisitMedicationSummary(
                        drug_id=m.drug_id,
                        drug_name=m.drug_name,
                        drug_class_note=m.drug_class_note,
                        dose_value=m.dose_value,
                        dose_unit=m.dose_unit,
                    )
                    for m in v.medications
                ],
                observations=[
                    VisitObservationSummary(
                        loinc_code=o.loinc_code,
                        display_name=o.display_name,
                        value=o.value,
                        unit=o.unit,
                    )
                    for o in v.observations
                ],
            )
            for v in sorted(patient.visits, key=lambda v: v.visit_number)
        ],
    )
