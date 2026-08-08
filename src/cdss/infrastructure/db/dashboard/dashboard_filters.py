"""Reusable SQL cohort filtering for dashboard aggregates."""

from datetime import date
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from cdss.infrastructure.db.models import Patient, PatientCondition, Visit


class DashboardFilterMixin:
    _session: Session

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
