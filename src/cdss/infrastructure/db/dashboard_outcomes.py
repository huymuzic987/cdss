"""SQL aggregation for dashboard blood-pressure outcomes."""

from datetime import date
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from cdss.infrastructure.db.dashboard_metrics import (
    _SBP_BUCKET_LAST,
    _SBP_BUCKETS,
    OutcomesCounts,
    VisitNumberAggregate,
)
from cdss.infrastructure.db.models import Visit


class DashboardOutcomesMixin:
    _session: Session
    _patient_ids_query: Any

    def outcomes_counts(
        self,
        *,
        today: date,
        department: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        gender: str | None = None,
        comorbidity_icd10: str | None = None,
        adherent_to_cdss: bool | None = None,
    ) -> OutcomesCounts:
        patient_ids = self._patient_ids_query(
            today=today,
            department=department,
            min_age=min_age,
            max_age=max_age,
            gender=gender,
            comorbidity_icd10=comorbidity_icd10,
            adherent_to_cdss=adherent_to_cdss,
        ).subquery()
        in_scope = Visit.patient_id.in_(select(patient_ids.c.id))

        target_rows = self._session.execute(
            select(Visit.bp_target_sbp, Visit.bp_target_dbp, func.count())
            .where(in_scope, Visit.bp_target_sbp.is_not(None), Visit.bp_target_dbp.is_not(None))
            .group_by(Visit.bp_target_sbp, Visit.bp_target_dbp)
        ).all()
        target_counts = {f"{sbp}/{dbp}": count for sbp, dbp, count in target_rows}

        outcome_rows = self._session.execute(
            select(
                Visit.visit_number,
                func.count().label("visit_count"),
                func.count().filter(Visit.bp_controlled.is_(True)).label("controlled_count"),
                func.count().filter(Visit.bp_controlled.is_not(None)).label("controlled_denom"),
                func.avg(Visit.clinic_sbp).label("avg_sbp"),
                func.avg(Visit.clinic_dbp).label("avg_dbp"),
            )
            .where(in_scope)
            .group_by(Visit.visit_number)
            .order_by(Visit.visit_number)
        ).all()
        by_visit_number = [
            VisitNumberAggregate(
                visit_number=row.visit_number,
                count=row.visit_count,
                bp_controlled_rate=(row.controlled_count / row.controlled_denom)
                if row.controlled_denom
                else 0.0,
                avg_sbp=float(row.avg_sbp) if row.avg_sbp is not None else None,
                avg_dbp=float(row.avg_dbp) if row.avg_dbp is not None else None,
            )
            for row in outcome_rows
        ]

        sbp_bucket = case(
            *[(Visit.clinic_sbp < threshold, label) for threshold, label in _SBP_BUCKETS],
            else_=_SBP_BUCKET_LAST,
        )
        sbp_rows = self._session.execute(
            select(sbp_bucket, func.count())
            .where(in_scope, Visit.clinic_sbp.is_not(None))
            .group_by(sbp_bucket)
        ).all()

        sbp_stats = self._session.execute(
            select(
                func.avg(Visit.clinic_sbp),
                func.percentile_cont(0.5).within_group(Visit.clinic_sbp),
            ).where(in_scope, Visit.clinic_sbp.is_not(None))
        ).first()
        mean_sbp = float(sbp_stats[0]) if sbp_stats and sbp_stats[0] is not None else None
        median_sbp = float(sbp_stats[1]) if sbp_stats and sbp_stats[1] is not None else None

        return OutcomesCounts(
            target_counts=target_counts,
            by_visit_number=by_visit_number,
            sbp_severity_counts={label: count for label, count in sbp_rows},
            mean_sbp=mean_sbp,
            median_sbp=median_sbp,
        )
