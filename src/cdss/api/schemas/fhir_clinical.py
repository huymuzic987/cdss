"""Hand-written HL7 FHIR R4 schemas for clinical data (patients/visits) that
back the statistics dashboard.

Companion to ``fhir.py`` (which exports the decision-tree knowledge base as
PlanDefinition/Library). This module covers the clinical side: Patient,
Condition, Encounter, Observation, MedicationRequest -- only the fields the
dashboard actually reads or writes.

Coding choices are aligned with the project's real reference data
(``backups/test_case/*.json``) rather than invented ones: SBP uses LOINC
8459-0 (sitting systolic BP, matching the reference bundles) not the generic
8480-6; Condition uses real ICD-10 (+ optional SNOMED CT); MedicationRequest
carries a real drug name, dose, and drug-class note. Two extension
namespaces are used side by side: ``AI4LIFE_BASE`` for concepts the
reference data already defines (department, cdss-adherent), and
``EXT_BASE`` for CDSS-specific concepts that vocabulary doesn't have
(visit-number, BP target, recommended action, ...).

Import is intentionally lenient (plain dict parsing in
``cdss.infrastructure.db.clinical_import``, not strict pydantic validation)
since real-world FHIR bundles vary in shape; these models are used for
*export* (serializing our own data back out as FHIR) and for typed API
responses.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from cdss.api.schemas.fhir import CodeableConcept, Coding, FhirModel

EXT_BASE = "http://cdss.local/fhir/StructureDefinition"
AI4LIFE_BASE = "http://example.org/fhir/ai4life/StructureDefinition"

EXT_RISK_FACTOR_COUNT = f"{EXT_BASE}/risk-factor-count"
EXT_VISIT_NUMBER = f"{EXT_BASE}/visit-number"
EXT_IS_EARLY_REVISIT = f"{EXT_BASE}/is-early-revisit"
EXT_EARLY_REVISIT_REASON = f"{EXT_BASE}/early-revisit-reason"
EXT_SCHEDULED_NEXT_VISIT = f"{EXT_BASE}/scheduled-next-visit-date"
EXT_HYPERTENSION_CLASS = f"{EXT_BASE}/hypertension-class"
EXT_RISK_LEVEL = f"{EXT_BASE}/risk-level"
EXT_BP_TARGET_SBP = f"{EXT_BASE}/bp-target-sbp"
EXT_BP_TARGET_DBP = f"{EXT_BASE}/bp-target-dbp"
EXT_CDSS_RECOMMENDED_ACTION = f"{EXT_BASE}/cdss-recommended-action"
EXT_FACILITY_CAPABILITY = f"{EXT_BASE}/facility-capability"

EXT_DEPARTMENT = f"{AI4LIFE_BASE}/department"
EXT_ADHERENT_TO_CDSS = f"{AI4LIFE_BASE}/cdss-adherent"

SYS_LOINC = "http://loinc.org"
SYS_ICD10 = "http://hl7.org/fhir/sid/icd-10"
SYS_SNOMED = "http://snomed.info/sct"
SYS_UCUM = "http://unitsofmeasure.org"

LOINC_SBP_CODE = "8459-0"
LOINC_SBP_DISPLAY = "Huyết áp tâm thu (ngồi)"
LOINC_DBP_CODE = "8462-4"
LOINC_DBP_DISPLAY = "Huyết áp tâm trương"


class ClinicalExtension(FhirModel):
    """Extension with the broader set of value[x] variants clinical resources need
    (fhir.py's Extension only models valueString/valueInteger)."""

    url: str
    value_string: str | None = Field(default=None, alias="valueString")
    value_integer: int | None = Field(default=None, alias="valueInteger")
    value_boolean: bool | None = Field(default=None, alias="valueBoolean")
    value_date: str | None = Field(default=None, alias="valueDate")


class Reference(FhirModel):
    reference: str


class Quantity(FhirModel):
    value: float
    unit: str
    system: str | None = None
    code: str | None = None


class Period(FhirModel):
    start: str
    end: str | None = None


class Patient(FhirModel):
    resource_type: Literal["Patient"] = Field(default="Patient", alias="resourceType")
    id: str
    gender: str | None = None
    birth_date: str | None = Field(default=None, alias="birthDate")
    extension: list[ClinicalExtension] | None = None

    @classmethod
    def from_row(
        cls,
        *,
        fhir_id: str,
        gender: str | None,
        birth_date: str | None,
        risk_factor_count: int,
        department: str | None = None,
    ) -> Patient:
        extensions = [ClinicalExtension(url=EXT_RISK_FACTOR_COUNT, valueInteger=risk_factor_count)]
        if department:
            extensions.append(ClinicalExtension(url=EXT_DEPARTMENT, valueString=department))
        return cls(id=fhir_id, gender=gender, birthDate=birth_date, extension=extensions)


class Condition(FhirModel):
    resource_type: Literal["Condition"] = Field(default="Condition", alias="resourceType")
    id: str
    subject: Reference
    code: CodeableConcept

    @classmethod
    def from_row(
        cls,
        *,
        condition_id: str,
        patient_fhir_id: str,
        icd10_code: str | None,
        snomed_code: str | None,
        condition_text: str | None,
    ) -> Condition:
        codings = []
        if icd10_code:
            codings.append(Coding(system=SYS_ICD10, code=icd10_code))
        if snomed_code:
            codings.append(Coding(system=SYS_SNOMED, code=snomed_code))
        return cls(
            id=condition_id,
            subject=Reference(reference=f"Patient/{patient_fhir_id}"),
            code=CodeableConcept(coding=codings, text=condition_text),
        )


class Encounter(FhirModel):
    resource_type: Literal["Encounter"] = Field(default="Encounter", alias="resourceType")
    id: str
    status: Literal["finished"] = "finished"
    class_: Coding = Field(alias="class")
    subject: Reference
    period: Period
    extension: list[ClinicalExtension] = Field(default_factory=list)

    @classmethod
    def from_visit(
        cls, *, encounter_id: str, patient_fhir_id: str, visit: dict[str, Any]
    ) -> Encounter:
        extensions = [
            ClinicalExtension(url=EXT_VISIT_NUMBER, valueInteger=visit["visit_number"]),
            ClinicalExtension(url=EXT_IS_EARLY_REVISIT, valueBoolean=visit["is_early_revisit"]),
        ]
        if visit.get("facility_capability"):
            extensions.append(
                ClinicalExtension(
                    url=EXT_FACILITY_CAPABILITY, valueString=visit["facility_capability"]
                )
            )
        if visit.get("early_revisit_reason"):
            extensions.append(
                ClinicalExtension(
                    url=EXT_EARLY_REVISIT_REASON, valueString=visit["early_revisit_reason"]
                )
            )
        if visit.get("scheduled_next_visit_date"):
            extensions.append(
                ClinicalExtension(
                    url=EXT_SCHEDULED_NEXT_VISIT, valueDate=visit["scheduled_next_visit_date"]
                )
            )
        if visit.get("hypertension_class"):
            extensions.append(
                ClinicalExtension(
                    url=EXT_HYPERTENSION_CLASS, valueString=visit["hypertension_class"]
                )
            )
        if visit.get("risk_level"):
            extensions.append(
                ClinicalExtension(url=EXT_RISK_LEVEL, valueString=visit["risk_level"])
            )
        if visit.get("bp_target_sbp") is not None:
            extensions.append(
                ClinicalExtension(url=EXT_BP_TARGET_SBP, valueInteger=visit["bp_target_sbp"])
            )
        if visit.get("bp_target_dbp") is not None:
            extensions.append(
                ClinicalExtension(url=EXT_BP_TARGET_DBP, valueInteger=visit["bp_target_dbp"])
            )
        if visit.get("cdss_recommended_action"):
            extensions.append(
                ClinicalExtension(
                    url=EXT_CDSS_RECOMMENDED_ACTION, valueString=visit["cdss_recommended_action"]
                )
            )
        if visit.get("adherent_to_cdss") is not None:
            extensions.append(
                ClinicalExtension(url=EXT_ADHERENT_TO_CDSS, valueBoolean=visit["adherent_to_cdss"])
            )
        # "class" is a reserved word, so this is built via model_validate(alias-keyed dict)
        # rather than the __init__ keyword form (which pyright resolves to the alias name).
        return cls.model_validate(
            {
                "id": encounter_id,
                "class": {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "AMB",
                    "display": "ambulatory",
                },
                "subject": {"reference": f"Patient/{patient_fhir_id}"},
                "period": {"start": str(visit["visit_date"])},
                "extension": [e.model_dump(by_alias=True, exclude_none=True) for e in extensions],
            }
        )


class Observation(FhirModel):
    resource_type: Literal["Observation"] = Field(default="Observation", alias="resourceType")
    id: str
    status: Literal["final"] = "final"
    code: CodeableConcept
    subject: Reference
    encounter: Reference | None = None
    value_quantity: Quantity = Field(alias="valueQuantity")

    @classmethod
    def from_reading(
        cls,
        *,
        observation_id: str,
        patient_fhir_id: str,
        encounter_id: str | None,
        loinc_code: str,
        display: str | None,
        value: float,
        unit: str,
        ucum_code: str | None = None,
    ) -> Observation:
        coding = Coding(system=SYS_LOINC, code=loinc_code, display=display)
        return cls(
            id=observation_id,
            code=CodeableConcept(coding=[coding]),
            subject=Reference(reference=f"Patient/{patient_fhir_id}"),
            encounter=Reference(reference=f"Encounter/{encounter_id}") if encounter_id else None,
            valueQuantity=Quantity(value=value, unit=unit, system=SYS_UCUM, code=ucum_code or unit),
        )

    @classmethod
    def blood_pressure_pair(
        cls,
        *,
        observation_id_prefix: str,
        patient_fhir_id: str,
        encounter_id: str | None,
        sbp: float,
        dbp: float,
    ) -> list[Observation]:
        return [
            cls.from_reading(
                observation_id=f"{observation_id_prefix}-sbp",
                patient_fhir_id=patient_fhir_id,
                encounter_id=encounter_id,
                loinc_code=LOINC_SBP_CODE,
                display=LOINC_SBP_DISPLAY,
                value=sbp,
                unit="mmHg",
                ucum_code="mm[Hg]",
            ),
            cls.from_reading(
                observation_id=f"{observation_id_prefix}-dbp",
                patient_fhir_id=patient_fhir_id,
                encounter_id=encounter_id,
                loinc_code=LOINC_DBP_CODE,
                display=LOINC_DBP_DISPLAY,
                value=dbp,
                unit="mmHg",
                ucum_code="mm[Hg]",
            ),
        ]


class DoseAndRate(FhirModel):
    dose_quantity: Quantity = Field(alias="doseQuantity")


class DosageInstruction(FhirModel):
    dose_and_rate: list[DoseAndRate] = Field(alias="doseAndRate")


class MedicationNote(FhirModel):
    text: str


class MedicationRequest(FhirModel):
    resource_type: Literal["MedicationRequest"] = Field(
        default="MedicationRequest", alias="resourceType"
    )
    id: str
    status: Literal["active", "completed"] = "active"
    intent: Literal["order"] = "order"
    medication_codeable_concept: CodeableConcept = Field(alias="medicationCodeableConcept")
    subject: Reference
    encounter: Reference | None = None
    authored_on: str | None = Field(default=None, alias="authoredOn")
    note: list[MedicationNote] | None = None
    dosage_instruction: list[DosageInstruction] | None = Field(
        default=None, alias="dosageInstruction"
    )

    @classmethod
    def from_row(
        cls,
        *,
        request_id: str,
        patient_fhir_id: str,
        encounter_id: str | None,
        drug_name: str,
        drug_class_note: str | None,
        dose_value: float | None,
        dose_unit: str | None,
        authored_on: str | None,
    ) -> MedicationRequest:
        dosage = None
        if dose_value is not None:
            dosage = [
                DosageInstruction(
                    doseAndRate=[
                        DoseAndRate(
                            doseQuantity=Quantity(
                                value=dose_value,
                                unit=dose_unit or "mg",
                                system=SYS_UCUM,
                                code=dose_unit or "mg",
                            )
                        )
                    ]
                )
            ]
        note = [MedicationNote(text=f"drugClass: {drug_class_note}")] if drug_class_note else None
        return cls(
            id=request_id,
            medicationCodeableConcept=CodeableConcept(text=drug_name),
            subject=Reference(reference=f"Patient/{patient_fhir_id}"),
            encounter=Reference(reference=f"Encounter/{encounter_id}") if encounter_id else None,
            authoredOn=authored_on,
            note=note,
            dosageInstruction=dosage,
        )


class BundleEntry(FhirModel):
    full_url: str | None = Field(default=None, alias="fullUrl")
    resource: dict[str, Any]


class Bundle(FhirModel):
    resource_type: Literal["Bundle"] = Field(default="Bundle", alias="resourceType")
    type: Literal["collection", "searchset"] = "collection"
    entry: list[BundleEntry] = Field(default_factory=list)


class ImportResult(FhirModel):
    source_label: str
    patients_imported: int
    visits_imported: int
    error_count: int
    errors: list[dict[str, str]]
