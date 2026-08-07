"""FHIR import status and attention-list response builders."""

from datetime import date

from cdss.api.routes.dashboard_common import last_visit
from cdss.api.schemas.dashboard import (
    FhirImportStatusResponse,
    ImportBatchSummary,
    NeedsAttentionPatient,
    NeedsAttentionResponse,
)
from cdss.infrastructure.db.dashboard.dashboard_repository import DashboardRepository
from cdss.infrastructure.db.models import Patient


def _build_fhir_import_status(
    repository: DashboardRepository, patients: list[Patient]
) -> FhirImportStatusResponse:
    batches = repository.list_import_batches()
    all_visits = [v for p in patients for v in p.visits]
    total_visits = len(all_visits)
    # Every visit has an SBP + DBP reading (dedicated columns) plus whatever
    # generic labs (eGFR, potassium, ...) landed in visit_observations.
    total_observations = sum(
        (2 if v.clinic_sbp is not None and v.clinic_dbp is not None else 0) + len(v.observations)
        for v in all_visits
    )
    return FhirImportStatusResponse(
        batches=[
            ImportBatchSummary(
                source_label=b.source_label,
                imported_at=b.imported_at,
                patient_count=b.patient_count,
                visit_count=b.visit_count,
                error_count=b.error_count,
            )
            for b in batches
        ],
        total_patients=len(patients),
        total_encounters=total_visits,
        total_observations=total_observations,
        total_medication_requests=sum(len(v.medications) for v in all_visits),
    )


def _build_needs_attention(
    patients: list[Patient], today: date, *, limit: int
) -> NeedsAttentionResponse:
    results: list[NeedsAttentionPatient] = []
    for p in patients:
        last = last_visit(p)
        if last is None:
            continue
        reasons: list[str] = []
        if last.bp_controlled is False:
            reasons.append("BP_NOT_CONTROLLED")
        if last.scheduled_next_visit_date and last.scheduled_next_visit_date < today:
            reasons.append("OVERDUE")
        if last.is_early_revisit:
            reasons.append("RECENT_EARLY_REVISIT")
        if reasons:
            results.append(
                NeedsAttentionPatient(
                    patient_fhir_id=p.fhir_id,
                    reasons=reasons,
                    last_visit_date=last.visit_date,
                    clinic_sbp=last.clinic_sbp,
                    clinic_dbp=last.clinic_dbp,
                    bp_target_sbp=last.bp_target_sbp,
                    bp_target_dbp=last.bp_target_dbp,
                )
            )
    results.sort(key=lambda r: len(r.reasons), reverse=True)
    return NeedsAttentionResponse(patients=results[:limit])
