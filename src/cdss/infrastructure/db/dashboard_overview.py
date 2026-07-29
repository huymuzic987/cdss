"""SQL aggregation for the dashboard overview section."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from cdss.infrastructure.db.dashboard_metrics import (
    _AGE_BUCKET_LAST,
    _AGE_BUCKETS,
    OverviewCounts,
    risk_factor_bucket_label,
)
from cdss.infrastructure.db.models import Patient, PatientCondition, Visit


class DashboardOverviewMixin:
    _session: Session
    _patient_ids_query: Any

    def overview_counts(
        self,
        *,
        today: date,
        department: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        gender: str | None = None,
        comorbidity_icd10: str | None = None,
        adherent_to_cdss: bool | None = None,
    ) -> OverviewCounts:
        patient_ids = self._patient_ids_query(
            today=today,
            department=department,
            min_age=min_age,
            max_age=max_age,
            gender=gender,
            comorbidity_icd10=comorbidity_icd10,
            adherent_to_cdss=adherent_to_cdss,
        ).subquery()
        in_scope = Patient.id.in_(select(patient_ids.c.id))

        total_patients = self._session.execute(
            select(func.count()).select_from(patient_ids)
        ).scalar_one()

        total_visits = self._session.execute(
            select(func.count(Visit.id)).where(Visit.patient_id.in_(select(patient_ids.c.id)))
        ).scalar_one()

        first_visit = (
            select(Visit.patient_id, func.min(Visit.visit_date).label("first_visit_date"))
            .where(Visit.patient_id.in_(select(patient_ids.c.id)))
            .group_by(Visit.patient_id)
            .subquery()
        )
        new_patients = self._session.execute(
            select(func.count())
            .select_from(first_visit)
            .where(first_visit.c.first_visit_date >= today - timedelta(days=30))
        ).scalar_one()

        age_years = func.extract("year", func.age(today, Patient.birth_date))
        age_bucket = case(
            (Patient.birth_date.is_(None), "Unknown"),
            *[(age_years < threshold, label) for threshold, label in _AGE_BUCKETS],
            else_=_AGE_BUCKET_LAST,
        )
        age_rows = self._session.execute(
            select(age_bucket, func.count()).where(in_scope).group_by(age_bucket)
        ).all()

        gender_key = func.coalesce(Patient.gender, "unknown")
        gender_rows = self._session.execute(
            select(gender_key, func.count()).where(in_scope).group_by(gender_key)
        ).all()

        # Exclude the primary hypertension diagnosis (I10) -- every patient has
        # it by definition, so it isn't a useful "comorbidity" prevalence stat.
        comorbidity_rows = self._session.execute(
            select(
                PatientCondition.icd10_code, func.count(func.distinct(PatientCondition.patient_id))
            )
            .where(
                PatientCondition.patient_id.in_(select(patient_ids.c.id)),
                PatientCondition.icd10_code.is_not(None),
                PatientCondition.icd10_code != "I10",
            )
            .group_by(PatientCondition.icd10_code)
        ).all()

        risk_factor_rows = self._session.execute(
            select(Patient.risk_factor_count, func.count())
            .where(in_scope)
            .group_by(Patient.risk_factor_count)
        ).all()
        risk_factor_counts: dict[str, int] = {}
        for count, n in risk_factor_rows:
            label = risk_factor_bucket_label(count)
            risk_factor_counts[label] = risk_factor_counts.get(label, 0) + n

        return OverviewCounts(
            total_patients=total_patients,
            total_visits=total_visits,
            new_patients_last_30_days=new_patients,
            age_counts={label: count for label, count in age_rows},
            gender_counts={label: count for label, count in gender_rows},
            comorbidity_counts={code: count for code, count in comorbidity_rows if code},
            risk_factor_counts=risk_factor_counts,
        )
