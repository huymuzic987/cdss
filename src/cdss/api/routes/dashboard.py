"""Statistics dashboard summary endpoint, patient search/detail, plus the
seed-data loader.

``overview``/``outcomes`` aggregate with SQL GROUP BY (see
``DashboardRepository.overview_counts``/``outcomes_counts``). The rest still
aggregate in Python over the full patient/visit set -- see
``DashboardRepository`` for why. Every section respects the same filter set
(department, age range, gender, comorbidity, CDSS adherence), applied
uniformly via one shared patient load per request.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_dashboard_repository
from cdss.api.schemas.dashboard import (
    AdherenceByVisitNumber,
    CdssUsageResponse,
    Count,
    DashboardSummaryResponse,
    EfficacyResponse,
    FhirImportStatusResponse,
    ImportBatchSummary,
    NeedsAttentionPatient,
    NeedsAttentionResponse,
    OutcomesResponse,
    OverdueVisit,
    OverviewResponse,
    PatientConditionSummary,
    PatientDetailResponse,
    PatientListItem,
    PatientListResponse,
    PatientVisitDetail,
    RatePoint,
    VisitMedicationSummary,
    VisitNumberOutcome,
    VisitObservationSummary,
    VisitsResponse,
)
from cdss.api.schemas.fhir_clinical import ImportResult
from cdss.core.database import get_db
from cdss.infrastructure.db.clinical_import import import_bundle
from cdss.infrastructure.db.dashboard_repository import (
    AGE_BUCKET_ORDER,
    SBP_BUCKET_ORDER,
    DashboardRepository,
    invalidate_cache,
)
from cdss.infrastructure.db.models import Patient, Visit

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = _REPO_ROOT / "data" / "fhir"
_TEST_CASE_DIR = _REPO_ROOT / "data" / "fhir" / "test_case"


def _today() -> date:
    return datetime.now(UTC).date()


def _rate(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else 0.0


def _last_visit(patient: Patient) -> Visit | None:
    return max(patient.visits, key=lambda v: v.visit_number) if patient.visits else None


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
        invalidate_cache()
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
    result = import_bundle(session, bundle, source_label=source)
    invalidate_cache()
    return result


class _Filters:
    """Bundles the dashboard's shared filter set so every ``_build_*``
    helper and the repository calls below take the same six params."""

    def __init__(
        self,
        department: str | None,
        min_age: int | None,
        max_age: int | None,
        gender: str | None,
        comorbidity_icd10: str | None,
        adherent_to_cdss: bool | None,
    ) -> None:
        self.department = department
        self.min_age = min_age
        self.max_age = max_age
        self.gender = gender
        self.comorbidity_icd10 = comorbidity_icd10
        self.adherent_to_cdss = adherent_to_cdss

    def as_kwargs(self) -> dict[str, str | int | bool | None]:
        return {
            "department": self.department,
            "min_age": self.min_age,
            "max_age": self.max_age,
            "gender": self.gender,
            "comorbidity_icd10": self.comorbidity_icd10,
            "adherent_to_cdss": self.adherent_to_cdss,
        }


def _build_overview(repository: DashboardRepository, today: date, filters: _Filters) -> OverviewResponse:
    stats = repository.overview_counts(today=today, **filters.as_kwargs())
    return OverviewResponse(
        total_patients=stats.total_patients,
        total_visits=stats.total_visits,
        new_patients_last_30_days=stats.new_patients_last_30_days,
        age_distribution=[
            Count(label=k, count=stats.age_counts[k]) for k in AGE_BUCKET_ORDER if k in stats.age_counts
        ],
        gender_distribution=[
            Count(label=k, count=v) for k, v in sorted(stats.gender_counts.items())
        ],
        comorbidity_prevalence=sorted(
            (
                RatePoint(label=k, count=v, rate=_rate(v, stats.total_patients))
                for k, v in stats.comorbidity_counts.items()
            ),
            key=lambda r: r.count,
            reverse=True,
        ),
        risk_factor_distribution=[
            Count(label=k, count=v) for k, v in sorted(stats.risk_factor_counts.items())
        ],
    )


def _build_visits(patients: list[Patient], today: date) -> VisitsResponse:
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


def _build_outcomes(repository: DashboardRepository, today: date, filters: _Filters) -> OutcomesResponse:
    stats = repository.outcomes_counts(today=today, **filters.as_kwargs())
    return OutcomesResponse(
        bp_target_distribution=sorted(
            (Count(label=k, count=v) for k, v in stats.target_counts.items()),
            key=lambda c: c.count,
            reverse=True,
        ),
        outcomes_by_visit_number=[
            VisitNumberOutcome(
                visit_number=agg.visit_number,
                count=agg.count,
                bp_controlled_rate=agg.bp_controlled_rate,
                avg_sbp=agg.avg_sbp,
                avg_dbp=agg.avg_dbp,
            )
            for agg in stats.by_visit_number
        ],
        sbp_severity_distribution=[
            Count(label=k, count=stats.sbp_severity_counts[k])
            for k in SBP_BUCKET_ORDER
            if k in stats.sbp_severity_counts
        ],
        mean_sbp=stats.mean_sbp,
        median_sbp=stats.median_sbp,
    )


def _build_cdss_usage(repository: DashboardRepository, patients: list[Patient]) -> CdssUsageResponse:
    all_visits = [v for p in patients for v in p.visits]

    def _tally(values: list[str]) -> dict[str, int]:
        tally: dict[str, int] = {}
        for value in values:
            tally[value] = tally.get(value, 0) + 1
        return tally

    def _counts(values: list[str]) -> list[Count]:
        return sorted(
            (Count(label=k, count=v) for k, v in _tally(values).items()),
            key=lambda c: c.count,
            reverse=True,
        )

    # These two are colored with an ordinal (severity) ramp on the frontend,
    # so they need to come back in clinical order rather than by frequency --
    # otherwise "darker = more severe" would be coloring the wrong bars.
    hypertension_class_order = ["NORMAL_BP", "HIGH_NORMAL_BP", "GRADE_1_HYPERTENSION", "GRADE_2_HYPERTENSION"]
    risk_level_order = ["LOW", "MEDIUM", "HIGH"]

    hypertension_tally = _tally([v.hypertension_class for v in all_visits if v.hypertension_class])
    risk_level_tally = _tally([v.risk_level for v in all_visits if v.risk_level])

    return CdssUsageResponse(
        facility_capability_distribution=_counts(
            [v.facility_capability for v in all_visits if v.facility_capability]
        ),
        hypertension_class_distribution=[
            Count(label=k, count=hypertension_tally[k]) for k in hypertension_class_order if k in hypertension_tally
        ],
        risk_level_distribution=[
            Count(label=k, count=risk_level_tally[k]) for k in risk_level_order if k in risk_level_tally
        ],
        recommended_action_frequency=_counts(
            [v.cdss_recommended_action for v in all_visits if v.cdss_recommended_action]
        )[:10],
        drug_class_distribution=sorted(
            (Count(label=k, count=v) for k, v in repository.drug_class_counts().items()),
            key=lambda c: c.count,
            reverse=True,
        ),
    )


def _build_efficacy(patients: list[Patient]) -> EfficacyResponse:
    all_visits = [v for p in patients for v in p.visits]

    adherence_flagged = [v for v in all_visits if v.adherent_to_cdss is not None]
    adherent_count = sum(1 for v in adherence_flagged if v.adherent_to_cdss)
    overall_rate = _rate(adherent_count, len(adherence_flagged))

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
        adherent_visit_count=adherent_count,
        non_adherent_visit_count=len(adherence_flagged) - adherent_count,
    )


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


def _build_needs_attention(patients: list[Patient], today: date, *, limit: int) -> NeedsAttentionResponse:
    results: list[NeedsAttentionPatient] = []
    for p in patients:
        last = _last_visit(p)
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
    today = _today()
    filters = _Filters(department, min_age, max_age, gender, comorbidity_icd10, adherent_to_cdss)
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
    today = _today()

    def _matches(p: Patient) -> bool:
        if gender and (p.gender or "unknown") != gender:
            return False
        if q:
            needle = q.strip().lower()
            haystack = f"{p.fhir_id} {p.department or ''}".lower()
            if needle not in haystack:
                return False
        if status:
            last = _last_visit(p)
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
        last = _last_visit(p)
        return last.visit_date if last else date.min

    matched = [p for p in repository.list_patients() if _matches(p)]
    matched.sort(key=_sort_key, reverse=True)

    page = matched[offset : offset + limit]
    items = []
    for p in page:
        last = _last_visit(p)
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
                    last and last.scheduled_next_visit_date and last.scheduled_next_visit_date < today
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
