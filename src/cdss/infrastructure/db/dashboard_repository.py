"""Read access to patients/visits for the statistics dashboard.

Loads full rows into Python and aggregates there rather than with SQL
GROUP BY: at the scale this dashboard targets (~1000 patients, a few
thousand visits) that is simpler to write and verify than hand-rolled
aggregate SQL, at an acceptable memory cost.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from cdss.infrastructure.db.models import FhirImportBatch, Patient, Visit


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_patients(
        self, *, facility_capability: str | None = None, comorbidity_icd10: str | None = None
    ) -> list[Patient]:
        """``comorbidity_icd10`` filters to patients with a matching
        ``PatientCondition.icd10_code`` (e.g. "N18" for chronic kidney
        disease) -- not the primary hypertension diagnosis every patient has.
        """
        stmt = select(Patient).options(
            selectinload(Patient.visits).selectinload(Visit.medications),
            selectinload(Patient.visits).selectinload(Visit.observations),
            selectinload(Patient.conditions),
        )
        patients = list(self._session.execute(stmt).scalars())
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
