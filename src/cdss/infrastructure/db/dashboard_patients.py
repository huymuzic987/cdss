"""Cached patient read model and ancillary dashboard queries."""

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from cdss.infrastructure.db.models import (
    FhirImportBatch,
    Medicine,
    Patient,
    Visit,
    VisitMedication,
)

_patients_cache: list[Patient] | None = None


def invalidate_cache() -> None:
    global _patients_cache
    _patients_cache = None


class DashboardPatientsMixin:
    _session: Session

    def drug_class_counts(self) -> dict[str, int]:
        drug_class_bucket = case(
            (Medicine.drug_class == "A", "RAAS (ACE / ARB / ARNI)"),
            (Medicine.drug_class == "D", "Diuretics"),
            (Medicine.drug_class == "MRA", "MRA"),
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
        facility_capability: str | None = None,
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
        if facility_capability:
            patients = [
                p
                for p in patients
                if any(v.facility_capability == facility_capability for v in p.visits)
            ]
        if gender:
            patients = [p for p in patients if p.gender == gender]
        if min_age is not None or max_age is not None:
            today = date.today()
            filtered = []
            for p in patients:
                if p.birth_date is None:
                    continue
                age = (
                    today.year
                    - p.birth_date.year
                    - ((today.month, today.day) < (p.birth_date.month, p.birth_date.day))
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
                p for p in patients if any(v.adherent_to_cdss == adherent_to_cdss for v in p.visits)
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
