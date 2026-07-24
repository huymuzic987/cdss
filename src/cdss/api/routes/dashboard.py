"""Statistics dashboard aggregation endpoints, plus the seed-data loader.

Aggregation is done in Python over the full patient/visit set (see
``DashboardRepository``) rather than SQL GROUP BY -- simpler to write
correctly at this data scale.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_dashboard_repository
from cdss.api.schemas.dashboard import (
    AdherenceByVisitNumber,
    CdssUsageResponse,
    Count,
    EfficacyResponse,
    FhirImportStatusResponse,
    ImportBatchSummary,
    NeedsAttentionPatient,
    NeedsAttentionResponse,
    OutcomesResponse,
    OverdueVisit,
    OverviewResponse,
    RatePoint,
    VisitNumberOutcome,
    VisitsResponse,
)
from cdss.api.schemas.fhir_clinical import ImportResult
from cdss.core.database import get_db
from cdss.infrastructure.db.clinical_import import import_bundle
from cdss.infrastructure.db.dashboard_repository import DashboardRepository
from cdss.infrastructure.db.models import Patient, Visit

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = _REPO_ROOT / "data" / "fhir"
_TEST_CASE_DIR = _REPO_ROOT / "backups" / "test_case"


def _today() -> date:
    return datetime.now(UTC).date()


def _age_bucket(birth_date: date | None, today: date) -> str:
    if birth_date is None:
        return "Unknown"
    age = (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
    if age < 40:
        return "<40"
    if age < 55:
        return "40-54"
    if age < 70:
        return "55-69"
    return "70+"


def _rate(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else 0.0


@router.post("/seed", response_model=ImportResult)
def seed_dashboard_data(
    session: Annotated[Session, Depends(get_db)],
    source: Literal["preset", "synthetic", "real_test_case"] = Query(...),
) -> ImportResult:
    if source == "real_test_case":
        # backups/test_case/*.json -- the project's real reference data, one
        # single-snapshot Bundle per patient (see clinical_import.py's
        # implicit-visit handling for bundles with no Encounter resource).
        paths = sorted(_TEST_CASE_DIR.glob("*.json"))
        if not paths:
            raise HTTPException(status_code=404, detail=f"no test cases found in {_TEST_CASE_DIR}")
        patients_imported = visits_imported = error_count = 0
        errors: list[dict[str, str]] = []
        for path in paths:
            result = import_bundle(
                session, json.loads(path.read_text(encoding="utf-8")), source_label=source
            )
            patients_imported += result.patients_imported
            visits_imported += result.visits_imported
            error_count += result.error_count
            errors.extend(result.errors)
        return ImportResult(
            source_label=source,
            patients_imported=patients_imported,
            visits_imported=visits_imported,
            error_count=error_count,
            errors=errors,
        )

    path = _DATA_DIR / f"{source}_patients.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"seed file not found: {path.name}")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return import_bundle(session, bundle, source_label=source)


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    facility_capability: str | None = Query(default=None),
    comorbidity_icd10: str | None = Query(default=None),
) -> OverviewResponse:
    patients = repository.list_patients(
        facility_capability=facility_capability, comorbidity_icd10=comorbidity_icd10
    )
    today = _today()

    total_visits = sum(len(p.visits) for p in patients)
    new_patients = sum(
        1
        for p in patients
        if p.visits and min(v.visit_date for v in p.visits) >= today - timedelta(days=30)
    )

    age_counts: dict[str, int] = {}
    gender_counts: dict[str, int] = {}
    comorbidity_counts: dict[str, int] = {}
    for p in patients:
        age_counts[_age_bucket(p.birth_date, today)] = (
            age_counts.get(_age_bucket(p.birth_date, today), 0) + 1
        )
        gender_key = p.gender or "unknown"
        gender_counts[gender_key] = gender_counts.get(gender_key, 0) + 1
        # Exclude the primary hypertension diagnosis (I10) -- every patient has
        # it by definition, so it isn't a useful "comorbidity" prevalence stat.
        for condition in p.conditions:
            if condition.icd10_code and condition.icd10_code != "I10":
                comorbidity_counts[condition.icd10_code] = (
                    comorbidity_counts.get(condition.icd10_code, 0) + 1
                )

    total_patients = len(patients)
    return OverviewResponse(
        total_patients=total_patients,
        total_visits=total_visits,
        new_patients_last_30_days=new_patients,
        age_distribution=[Count(label=k, count=v) for k, v in sorted(age_counts.items())],
        gender_distribution=[Count(label=k, count=v) for k, v in sorted(gender_counts.items())],
        comorbidity_prevalence=sorted(
            (
                RatePoint(label=k, count=v, rate=_rate(v, total_patients))
                for k, v in comorbidity_counts.items()
            ),
            key=lambda r: r.count,
            reverse=True,
        ),
    )


@router.get("/visits", response_model=VisitsResponse)
def get_visits(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    facility_capability: str | None = Query(default=None),
    comorbidity_icd10: str | None = Query(default=None),
) -> VisitsResponse:
    patients = repository.list_patients(
        facility_capability=facility_capability, comorbidity_icd10=comorbidity_icd10
    )
    today = _today()

    all_visits = [v for p in patients for v in p.visits]
    follow_ups = [v for v in all_visits if v.visit_number > 1]
    early_count = sum(1 for v in follow_ups if v.is_early_revisit)

    reason_counts: dict[str, int] = {}
    for v in follow_ups:
        if v.is_early_revisit and v.early_revisit_reason:
            reason_counts[v.early_revisit_reason] = reason_counts.get(v.early_revisit_reason, 0) + 1

    gaps: list[int] = []
    visit_number_counts: dict[int, int] = {}
    overdue: list[OverdueVisit] = []
    for p in patients:
        visits_sorted = sorted(p.visits, key=lambda v: v.visit_number)
        for v in visits_sorted:
            visit_number_counts[v.visit_number] = visit_number_counts.get(v.visit_number, 0) + 1
        for prev, curr in zip(visits_sorted, visits_sorted[1:], strict=False):
            gaps.append((curr.visit_date - prev.visit_date).days)
        if visits_sorted:
            last = visits_sorted[-1]
            if last.scheduled_next_visit_date and last.scheduled_next_visit_date < today:
                overdue.append(
                    OverdueVisit(
                        patient_fhir_id=p.fhir_id,
                        last_visit_date=last.visit_date,
                        scheduled_next_visit_date=last.scheduled_next_visit_date,
                        days_overdue=(today - last.scheduled_next_visit_date).days,
                    )
                )
    overdue.sort(key=lambda o: o.days_overdue, reverse=True)

    return VisitsResponse(
        total_visits=len(all_visits),
        follow_up_visit_count=len(follow_ups),
        on_schedule_rate=1 - _rate(early_count, len(follow_ups)),
        early_revisit_rate=_rate(early_count, len(follow_ups)),
        early_revisit_reason_breakdown=sorted(
            (Count(label=k, count=v) for k, v in reason_counts.items()),
            key=lambda c: c.count,
            reverse=True,
        ),
        avg_days_between_visits=(sum(gaps) / len(gaps)) if gaps else None,
        visits_by_visit_number=[
            Count(label=str(k), count=v) for k, v in sorted(visit_number_counts.items())
        ],
        overdue_patients=overdue[:50],
    )


@router.get("/outcomes", response_model=OutcomesResponse)
def get_outcomes(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    facility_capability: str | None = Query(default=None),
    comorbidity_icd10: str | None = Query(default=None),
) -> OutcomesResponse:
    patients = repository.list_patients(
        facility_capability=facility_capability, comorbidity_icd10=comorbidity_icd10
    )
    all_visits = [v for p in patients for v in p.visits]

    target_counts: dict[str, int] = {}
    for v in all_visits:
        if v.bp_target_sbp and v.bp_target_dbp:
            key = f"{v.bp_target_sbp}/{v.bp_target_dbp}"
            target_counts[key] = target_counts.get(key, 0) + 1

    by_number: dict[int, list[Visit]] = {}
    for v in all_visits:
        by_number.setdefault(v.visit_number, []).append(v)

    outcomes = []
    for number, visits in sorted(by_number.items()):
        controlled = [v for v in visits if v.bp_controlled is not None]
        sbps = [v.clinic_sbp for v in visits if v.clinic_sbp is not None]
        dbps = [v.clinic_dbp for v in visits if v.clinic_dbp is not None]
        outcomes.append(
            VisitNumberOutcome(
                visit_number=number,
                count=len(visits),
                bp_controlled_rate=_rate(
                    sum(1 for v in controlled if v.bp_controlled), len(controlled)
                ),
                avg_sbp=(sum(sbps) / len(sbps)) if sbps else None,
                avg_dbp=(sum(dbps) / len(dbps)) if dbps else None,
            )
        )

    return OutcomesResponse(
        bp_target_distribution=sorted(
            (Count(label=k, count=v) for k, v in target_counts.items()),
            key=lambda c: c.count,
            reverse=True,
        ),
        outcomes_by_visit_number=outcomes,
    )


@router.get("/cdss-usage", response_model=CdssUsageResponse)
def get_cdss_usage(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
) -> CdssUsageResponse:
    patients = repository.list_patients()
    all_visits = [v for p in patients for v in p.visits]

    def _counts(values: list[str]) -> list[Count]:
        tally: dict[str, int] = {}
        for value in values:
            tally[value] = tally.get(value, 0) + 1
        return sorted(
            (Count(label=k, count=v) for k, v in tally.items()), key=lambda c: c.count, reverse=True
        )

    return CdssUsageResponse(
        facility_capability_distribution=_counts(
            [v.facility_capability for v in all_visits if v.facility_capability]
        ),
        hypertension_class_distribution=_counts(
            [v.hypertension_class for v in all_visits if v.hypertension_class]
        ),
        risk_level_distribution=_counts([v.risk_level for v in all_visits if v.risk_level]),
        recommended_action_frequency=_counts(
            [v.cdss_recommended_action for v in all_visits if v.cdss_recommended_action]
        )[:10],
    )


@router.get("/efficacy", response_model=EfficacyResponse)
def get_efficacy(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
) -> EfficacyResponse:
    patients = repository.list_patients()
    all_visits = [v for p in patients for v in p.visits]

    adherence_flagged = [v for v in all_visits if v.adherent_to_cdss is not None]
    overall_rate = _rate(
        sum(1 for v in adherence_flagged if v.adherent_to_cdss), len(adherence_flagged)
    )

    # Same-visit adherence vs. that same visit's BP control is circular: a
    # visit is only ever marked non-adherent when BP wasn't already controlled
    # (an already-controlled visit trivially "adheres" by maintaining the
    # regimen). The real question is whether following the recommendation at
    # an uncontrolled visit predicts control at the *next* visit, so compare
    # across consecutive visits instead.
    adherent_next_controlled = 0
    adherent_decision_points = 0
    nonadherent_next_controlled = 0
    nonadherent_decision_points = 0
    for p in patients:
        visits_sorted = sorted(p.visits, key=lambda v: v.visit_number)
        for prev, curr in zip(visits_sorted, visits_sorted[1:], strict=False):
            if prev.bp_controlled is not False or curr.bp_controlled is None:
                continue
            if prev.adherent_to_cdss is None:
                continue
            if prev.adherent_to_cdss:
                adherent_decision_points += 1
                adherent_next_controlled += 1 if curr.bp_controlled else 0
            else:
                nonadherent_decision_points += 1
                nonadherent_next_controlled += 1 if curr.bp_controlled else 0
    rate_adherent = _rate(adherent_next_controlled, adherent_decision_points)
    rate_nonadherent = _rate(nonadherent_next_controlled, nonadherent_decision_points)

    def _drug_set(visit: Visit) -> frozenset[str]:
        return frozenset(m.drug_id or m.drug_name for m in visit.medications)

    change_count = 0
    change_opportunities = 0
    for p in patients:
        visits_sorted = sorted(p.visits, key=lambda v: v.visit_number)
        for prev, curr in zip(visits_sorted, visits_sorted[1:], strict=False):
            if prev.medications and curr.medications:
                change_opportunities += 1
                if _drug_set(prev) != _drug_set(curr):
                    change_count += 1

    by_number: dict[int, list[Visit]] = {}
    for v in adherence_flagged:
        by_number.setdefault(v.visit_number, []).append(v)
    adherence_by_number = [
        AdherenceByVisitNumber(
            visit_number=number,
            adherence_rate=_rate(sum(1 for v in visits if v.adherent_to_cdss), len(visits)),
            count=len(visits),
        )
        for number, visits in sorted(by_number.items())
    ]

    return EfficacyResponse(
        overall_adherence_rate=overall_rate,
        bp_control_rate_when_adherent=rate_adherent,
        bp_control_rate_when_not_adherent=rate_nonadherent,
        effectiveness_delta=rate_adherent - rate_nonadherent,
        medication_change_count=change_count,
        medication_change_rate=_rate(change_count, change_opportunities),
        adherence_rate_by_visit_number=adherence_by_number,
    )


@router.get("/fhir-import-status", response_model=FhirImportStatusResponse)
def get_fhir_import_status(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
) -> FhirImportStatusResponse:
    batches = repository.list_import_batches()
    patients = repository.list_patients()
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


@router.get("/needs-attention", response_model=NeedsAttentionResponse)
def get_needs_attention(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    limit: int = Query(default=100, le=500),
) -> NeedsAttentionResponse:
    patients: list[Patient] = repository.list_patients()
    today = _today()
    results: list[NeedsAttentionPatient] = []
    for p in patients:
        if not p.visits:
            continue
        last = max(p.visits, key=lambda v: v.visit_number)
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
