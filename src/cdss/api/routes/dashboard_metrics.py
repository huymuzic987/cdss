"""Overview, visit, and outcome response builders."""

from datetime import date

from cdss.api.routes.dashboard_common import DashboardFilters, rate
from cdss.api.schemas.dashboard import (
    Count,
    OutcomesResponse,
    OverdueVisit,
    OverviewResponse,
    RatePoint,
    VisitNumberOutcome,
    VisitsResponse,
)
from cdss.infrastructure.db.dashboard.dashboard_repository import (
    AGE_BUCKET_ORDER,
    SBP_BUCKET_ORDER,
    DashboardRepository,
)
from cdss.infrastructure.db.models import Patient


def _build_overview(
    repository: DashboardRepository, today: date, filters: DashboardFilters
) -> OverviewResponse:
    stats = repository.overview_counts(today=today, **filters.as_kwargs())
    return OverviewResponse(
        total_patients=stats.total_patients,
        total_visits=stats.total_visits,
        new_patients_last_30_days=stats.new_patients_last_30_days,
        age_distribution=[
            Count(label=k, count=stats.age_counts[k])
            for k in AGE_BUCKET_ORDER
            if k in stats.age_counts
        ],
        gender_distribution=[
            Count(label=k, count=v) for k, v in sorted(stats.gender_counts.items())
        ],
        comorbidity_prevalence=sorted(
            (
                RatePoint(label=k, count=v, rate=rate(v, stats.total_patients))
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
        on_schedule_rate=1 - rate(early_count, len(follow_ups)),
        early_revisit_rate=rate(early_count, len(follow_ups)),
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


def _build_outcomes(
    repository: DashboardRepository, today: date, filters: DashboardFilters
) -> OutcomesResponse:
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
