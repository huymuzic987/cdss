"""CDSS usage and efficacy response builders."""

from cdss.api.routes.dashboard_common import rate
from cdss.api.schemas.dashboard import (
    AdherenceByVisitNumber,
    CdssUsageResponse,
    Count,
    EfficacyResponse,
)
from cdss.infrastructure.db.dashboard_repository import DashboardRepository
from cdss.infrastructure.db.models import Patient, Visit


def _build_cdss_usage(
    repository: DashboardRepository, patients: list[Patient]
) -> CdssUsageResponse:
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
    hypertension_class_order = [
        "NORMAL_BP",
        "HIGH_NORMAL_BP",
        "GRADE_1_HYPERTENSION",
        "GRADE_2_HYPERTENSION",
    ]
    risk_level_order = ["LOW", "MEDIUM", "HIGH"]

    hypertension_tally = _tally([v.hypertension_class for v in all_visits if v.hypertension_class])
    risk_level_tally = _tally([v.risk_level for v in all_visits if v.risk_level])

    return CdssUsageResponse(
        facility_capability_distribution=_counts(
            [v.facility_capability for v in all_visits if v.facility_capability]
        ),
        hypertension_class_distribution=[
            Count(label=k, count=hypertension_tally[k])
            for k in hypertension_class_order
            if k in hypertension_tally
        ],
        risk_level_distribution=[
            Count(label=k, count=risk_level_tally[k])
            for k in risk_level_order
            if k in risk_level_tally
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
    overallrate = rate(adherent_count, len(adherence_flagged))

    visits_sorted_by_patient = [sorted(p.visits, key=lambda v: v.visit_number) for p in patients]

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
    for visits_sorted in visits_sorted_by_patient:
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
    rate_adherent = rate(adherent_next_controlled, adherent_decision_points)
    rate_nonadherent = rate(nonadherent_next_controlled, nonadherent_decision_points)

    def _drug_set(visit: Visit) -> frozenset[str]:
        return frozenset(m.drug_id or m.drug_name for m in visit.medications)

    change_count = 0
    change_opportunities = 0
    for visits_sorted in visits_sorted_by_patient:
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
            adherence_rate=rate(sum(1 for v in visits if v.adherent_to_cdss), len(visits)),
            count=len(visits),
        )
        for number, visits in sorted(by_number.items())
    ]

    return EfficacyResponse(
        overall_adherence_rate=overallrate,
        bp_control_rate_when_adherent=rate_adherent,
        bp_control_rate_when_not_adherent=rate_nonadherent,
        effectiveness_delta=rate_adherent - rate_nonadherent,
        medication_change_count=change_count,
        medication_change_rate=rate(change_count, change_opportunities),
        adherence_rate_by_visit_number=adherence_by_number,
        adherent_visit_count=adherent_count,
        non_adherent_visit_count=len(adherence_flagged) - adherent_count,
    )
