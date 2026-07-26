"""Read access to patients/visits for the statistics dashboard.

``overview_counts``/``outcomes_counts`` aggregate with SQL GROUP BY. The
remaining endpoints (visits, cdss-usage, efficacy, fhir-import-status,
needs-attention) need cross-visit sequential logic -- e.g. comparing a
patient's consecutive visits -- that doesn't reduce cleanly to a single
GROUP BY, so they still load full rows into Python via ``list_patients``/
``_all_patients`` and aggregate there. At this dashboard's scale (~1000
patients, a few thousand visits) that's simpler to write and verify than
hand-rolled window-function SQL, at an acceptable memory cost.

The full graph fetch (``_all_patients``) is cached at module scope -- every
endpoint that needs it would otherwise re-run the same ~1000-patient eager
load on every request, even though the underlying data only changes via
``POST /dashboard/seed``. Call ``invalidate_cache()`` after a successful
seed import. This assumes a single worker process (see Dockerfile.backend)
-- a multi-worker deployment would need a shared cache (e.g. Redis) instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, selectinload

from cdss.infrastructure.db.models import FhirImportBatch, Patient, PatientCondition, Visit

_patients_cache: list[Patient] | None = None


def invalidate_cache() -> None:
    global _patients_cache
    _patients_cache = None


@dataclass
class OverviewCounts:
    total_patients: int
    total_visits: int
    new_patients_last_30_days: int
    age_counts: dict[str, int]
    gender_counts: dict[str, int]
    comorbidity_counts: dict[str, int]


@dataclass
class VisitNumberAggregate:
    visit_number: int
    count: int
    bp_controlled_rate: float
    avg_sbp: float | None
    avg_dbp: float | None


@dataclass
class OutcomesCounts:
    target_counts: dict[str, int]
    by_visit_number: list[VisitNumberAggregate]


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _patient_ids_query(
        self, facility_capability: str | None, comorbidity_icd10: str | None
    ) -> Select[Any]:
        """Patient ids matching the optional filters, as a reusable subquery
        -- mirrors ``list_patients``'s "any visit/condition matches" semantics.
        """
        stmt = select(Patient.id)
        if facility_capability:
            stmt = stmt.where(
                select(Visit.id)
                .where(
                    Visit.patient_id == Patient.id,
                    Visit.facility_capability == facility_capability,
                )
                .exists()
            )
        if comorbidity_icd10:
            stmt = stmt.where(
                select(PatientCondition.id)
                .where(
                    PatientCondition.patient_id == Patient.id,
                    PatientCondition.icd10_code == comorbidity_icd10,
                )
                .exists()
            )
        return stmt

    def overview_counts(
        self,
        *,
        today: date,
        facility_capability: str | None = None,
        comorbidity_icd10: str | None = None,
    ) -> OverviewCounts:
        patient_ids = self._patient_ids_query(facility_capability, comorbidity_icd10).subquery()

        total_patients = self._session.execute(
            select(func.count()).select_from(patient_ids)
        ).scalar_one()

        total_visits = self._session.execute(
            select(func.count(Visit.id)).where(
                Visit.patient_id.in_(select(patient_ids.c.id))
            )
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
            (age_years < 40, "<40"),
            (age_years < 55, "40-54"),
            (age_years < 70, "55-69"),
            else_="70+",
        )
        age_rows = self._session.execute(
            select(age_bucket, func.count())
            .where(Patient.id.in_(select(patient_ids.c.id)))
            .group_by(age_bucket)
        ).all()

        gender_key = func.coalesce(Patient.gender, "unknown")
        gender_rows = self._session.execute(
            select(gender_key, func.count())
            .where(Patient.id.in_(select(patient_ids.c.id)))
            .group_by(gender_key)
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

        return OverviewCounts(
            total_patients=total_patients,
            total_visits=total_visits,
            new_patients_last_30_days=new_patients,
            age_counts={label: count for label, count in age_rows},
            gender_counts={label: count for label, count in gender_rows},
            comorbidity_counts={code: count for code, count in comorbidity_rows if code},
        )

    def outcomes_counts(
        self, *, facility_capability: str | None = None, comorbidity_icd10: str | None = None
    ) -> OutcomesCounts:
        patient_ids = self._patient_ids_query(facility_capability, comorbidity_icd10).subquery()
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

        return OutcomesCounts(target_counts=target_counts, by_visit_number=by_visit_number)

    def _all_patients(self) -> list[Patient]:
        global _patients_cache
        if _patients_cache is None:
            stmt = select(Patient).options(
                selectinload(Patient.visits).selectinload(Visit.medications),
                selectinload(Patient.visits).selectinload(Visit.observations),
                selectinload(Patient.conditions),
            )
            patients = list(self._session.execute(stmt).scalars())
            self._session.expunge_all()
            _patients_cache = patients
        return _patients_cache

    def list_patients(
        self, *, facility_capability: str | None = None, comorbidity_icd10: str | None = None
    ) -> list[Patient]:
        """``comorbidity_icd10`` filters to patients with a matching
        ``PatientCondition.icd10_code`` (e.g. "N18" for chronic kidney
        disease) -- not the primary hypertension diagnosis every patient has.
        """
        patients = self._all_patients()
        if comorbidity_icd10:
            patients = [
                p for p in patients if any(c.icd10_code == comorbidity_icd10 for c in p.conditions)
            ]
        if facility_capability:
            patients = [
                p
                for p in patients
                if any(v.facility_capability == facility_capability for v in p.visits)
            ]
        return patients

    def list_import_batches(self, limit: int = 10) -> list[FhirImportBatch]:
        stmt = select(FhirImportBatch).order_by(FhirImportBatch.imported_at.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars())
