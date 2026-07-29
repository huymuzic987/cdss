"""Visit, observation, and medication persistence for FHIR imports."""

import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from cdss.api.schemas.fhir_clinical import LOINC_DBP_CODE, LOINC_SBP_CODE
from cdss.infrastructure.db.fhir_import_parsing import drug_class_note, medication_dose
from cdss.infrastructure.db.models import Patient, Visit, VisitMedication, VisitObservation


class ClinicalResourceWriter:
    def __init__(
        self,
        session: Session,
        errors: list[dict[str, str]],
        existing_visits: dict[str, Visit],
        medicine_by_name: dict[str, str],
    ) -> None:
        self.session = session
        self.errors = errors
        self.existing_visits = existing_visits
        self.medicine_by_name = medicine_by_name

    def apply_observations(self, visit: Visit, observations: list[dict[str, Any]]) -> None:
        self.session.execute(delete(VisitObservation).where(VisitObservation.visit_id == visit.id))
        for observation in observations:
            codings = (observation.get("code") or {}).get("coding") or []
            code = codings[0].get("code") if codings else None
            display = codings[0].get("display") if codings else None
            value = (observation.get("valueQuantity") or {}).get("value")
            unit = (observation.get("valueQuantity") or {}).get("unit")
            if code is None or value is None:
                self.errors.append({"resource": "Observation", "message": "missing code or value"})
                continue
            if code == LOINC_SBP_CODE:
                visit.clinic_sbp = int(value)
            elif code == LOINC_DBP_CODE:
                visit.clinic_dbp = int(value)
            else:
                self.session.add(
                    VisitObservation(
                        id=uuid.uuid4(),
                        visit_id=visit.id,
                        loinc_code=code,
                        display_name=display,
                        value=float(value),
                        unit=unit,
                    )
                )
        if (
            visit.clinic_sbp is not None
            and visit.clinic_dbp is not None
            and visit.bp_target_sbp
            and visit.bp_target_dbp
        ):
            visit.bp_controlled = (
                visit.clinic_sbp < visit.bp_target_sbp and visit.clinic_dbp < visit.bp_target_dbp
            )

    def apply_medications(self, visit: Visit, medications: list[dict[str, Any]]) -> None:
        self.session.execute(delete(VisitMedication).where(VisitMedication.visit_id == visit.id))
        for med_request in medications:
            drug_name = (med_request.get("medicationCodeableConcept") or {}).get("text")
            if not drug_name:
                self.errors.append(
                    {"resource": "MedicationRequest", "message": "missing medication text"}
                )
                continue
            dose_value, dose_unit = medication_dose(med_request)
            self.session.add(
                VisitMedication(
                    id=uuid.uuid4(),
                    visit_id=visit.id,
                    drug_id=self.medicine_by_name.get(drug_name.strip().lower()),
                    drug_name=drug_name,
                    drug_class_note=drug_class_note(med_request),
                    dose_value=dose_value,
                    dose_unit=dose_unit,
                )
            )

    def upsert_visit(self, fhir_encounter_id: str, patient: Patient, **fields: Any) -> Visit:
        visit = self.existing_visits.get(fhir_encounter_id)
        if visit is None:
            visit = Visit(
                id=uuid.uuid4(), patient_id=patient.id, fhir_encounter_id=fhir_encounter_id
            )
            self.session.add(visit)
            self.existing_visits[fhir_encounter_id] = visit
        visit.patient_id = patient.id
        for key, value in fields.items():
            setattr(visit, key, value)
        return visit
