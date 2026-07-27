"""Read access to patients/visits for the statistics dashboard.

``overview_counts``/``outcomes_counts`` aggregate with SQL GROUP BY. The
remaining sections (visits, cdss-usage, efficacy, fhir-import-status,
needs-attention, patient search) need cross-visit sequential logic -- e.g.
comparing a patient's consecutive visits -- that doesn't reduce cleanly to a
single GROUP BY, so they still load full rows into Python via
``list_patients``/``_all_patients`` and aggregate there. At this dashboard's
scale (~1000 patients, a few thousand visits) that's simpler to write and
verify than hand-rolled window-function SQL, at an acceptable memory cost.

The full graph fetch (``_all_patients``) is cached at module scope -- every
section that needs it would otherwise re-run the same ~1000-patient eager
load on every request, even though the underlying data only changes via
``POST /dashboard/seed``. Call ``invalidate_cache()`` after a successful
seed import. This assumes a single worker process (see Dockerfile.backend)
-- a multi-worker deployment would need a shared cache (e.g. Redis) instead.

Every filterable section (SQL and Python paths alike) respects the same
filter set -- department, age range, gender, comorbidity, CDSS adherence --
unlike the dashboard's previous per-section filter inconsistency.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, selectinload

from cdss.infrastructure.db.models import (
    FhirImportBatch,
    Medicine,
    Patient,
    PatientCondition,
    Visit,
    VisitMedication,
)

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
    risk_factor_counts: dict[str, int]


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
    sbp_severity_counts: dict[str, int]
    mean_sbp: float | None
    median_sbp: float | None


# Age-bucket / SBP-severity thresholds are shared between the SQL path
# (overview_counts/outcomes_counts) and the Python path (list_patients) so
# both produce identical bucket labels.
_AGE_BUCKETS = [(45, "<45"), (65, "45-64"), (75, "65-74")]
_AGE_BUCKET_LAST = "75+"
# Bucket labels don't sort into the right order alphabetically ("45-64" <
# "75+" < "<45" by string comparison) -- callers building a Count list use
# this to order rows the way the chart should read, not alphabetically.
AGE_BUCKET_ORDER = [label for _, label in _AGE_BUCKETS] + [_AGE_BUCKET_LAST, "Unknown"]

_SBP_BUCKETS = [
    (130, "SBP <130 mmHg"),
    (140, "SBP 130-139 mmHg"),
    (160, "SBP 140-159 mmHg"),
    (180, "SBP 160-179 mmHg"),
]
_SBP_BUCKET_LAST = "SBP >=180 mmHg"
SBP_BUCKET_ORDER = [label for _, label in _SBP_BUCKETS] + [_SBP_BUCKET_LAST]


def _risk_factor_bucket_label(count: int) -> str:
    return str(count) if count < 5 else "5+"


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _patient_ids_query(
        self,
        *,
        today: date,
        department: str | None,
        min_age: int | None,
        max_age: int | None,
        gender: str | None,
        comorbidity_icd10: str | None,
        adherent_to_cdss: bool | None,
    ) -> Select[Any]:
        """Patient ids matching the optional filters, as a reusable subquery
        -- mirrors ``list_patients``'s in-Python filtering semantics.
        """
        stmt = select(Patient.id)
        if department:
            stmt = stmt.where(Patient.department == department)
        if gender:
            stmt = stmt.where(Patient.gender == gender)
        if min_age is not None or max_age is not None:
            age_years = func.extract("year", func.age(today, Patient.birth_date))
            if min_age is not None:
                stmt = stmt.where(Patient.birth_date.is_not(None), age_years >= min_age)
            if max_age is not None:
                stmt = stmt.where(Patient.birth_date.is_not(None), age_years <= max_age)
        if comorbidity_icd10:
            stmt = stmt.where(
                select(PatientCondition.id)
                .where(
                    PatientCondition.patient_id == Patient.id,
                    PatientCondition.icd10_code == comorbidity_icd10,
                )
                .exists()
            )
        if adherent_to_cdss is not None:
            stmt = stmt.where(
                select(Visit.id)
                .where(
                    Visit.patient_id == Patient.id,
                    Visit.adherent_to_cdss == adherent_to_cdss,
                )
                .exists()
            )
        return stmt

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
            select(Patient.risk_factor_count, func.count()).where(in_scope).group_by(Patient.risk_factor_count)
        ).all()
        risk_factor_counts: dict[str, int] = {}
        for count, n in risk_factor_rows:
            label = _risk_factor_bucket_label(count)
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

    def drug_class_counts(self) -> dict[str, int]:
        drug_class_bucket = case(
            (Medicine.drug_class == "A", "RAAS (ACE / ARB / ARNI)"),
            (Medicine.drug_class == "D", "Diuretics & MRA"),
            (Medicine.drug_class == "C", "CCB"),
            (Medicine.drug_class == "B", "Beta-blockers"),
            else_="Other (central agents, vasodilators, ...)",
        )
        rows = self._session.execute(
            select(drug_class_bucket, func.count())
            .select_from(VisitMedication)
            .join(Medicine, Medicine.drug_id == VisitMedication.drug_id)
            .group_by(drug_class_bucket)
        ).all()
        return {label: count for label, count in rows}

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
        self,
        *,
        department: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        gender: str | None = None,
        comorbidity_icd10: str | None = None,
        adherent_to_cdss: bool | None = None,
    ) -> list[Patient]:
        """``comorbidity_icd10`` filters to patients with a matching
        ``PatientCondition.icd10_code`` (e.g. "N18" for chronic kidney
        disease) -- not the primary hypertension diagnosis every patient has.
        """
        patients = self._all_patients()
        if department:
            patients = [p for p in patients if p.department == department]
        if gender:
            patients = [p for p in patients if p.gender == gender]
        if min_age is not None or max_age is not None:
            today = date.today()
            filtered = []
            for p in patients:
                if p.birth_date is None:
                    continue
                age = today.year - p.birth_date.year - (
                    (today.month, today.day) < (p.birth_date.month, p.birth_date.day)
                )
                if min_age is not None and age < min_age:
                    continue
                if max_age is not None and age > max_age:
                    continue
                filtered.append(p)
            patients = filtered
        if comorbidity_icd10:
            patients = [
                p for p in patients if any(c.icd10_code == comorbidity_icd10 for c in p.conditions)
            ]
        if adherent_to_cdss is not None:
            patients = [
                p
                for p in patients
                if any(v.adherent_to_cdss == adherent_to_cdss for v in p.visits)
            ]
        return patients

    def get_patient_by_fhir_id(self, fhir_id: str) -> Patient | None:
        stmt = (
            select(Patient)
            .where(Patient.fhir_id == fhir_id)
            .options(
                selectinload(Patient.visits).selectinload(Visit.medications),
                selectinload(Patient.visits).selectinload(Visit.observations),
                selectinload(Patient.conditions),
            )
        )
        return self._session.execute(stmt).scalars().first()

    def list_import_batches(self, limit: int = 10) -> list[FhirImportBatch]:
        stmt = select(FhirImportBatch).order_by(FhirImportBatch.imported_at.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars())
