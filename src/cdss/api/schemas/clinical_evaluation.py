"""Canonical clinical FHIR Bundle -> decision-runtime translation.

Unlike the old evaluation-only FHIR dialect, this adapter consumes the same
Patient/Condition/Encounter/Observation/MedicationRequest resources used by
the clinical import API and the reference bundles in ``data/fhir/test_case``.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Never

from cdss.api.schemas.fhir_clinical import (
    EXT_BASE,
    EXT_FACILITY_CAPABILITY,
    EXT_RISK_FACTOR_COUNT,
    LOINC_DBP_CODE,
    LOINC_SBP_CODE,
)
from cdss.domain.decision_tree import InvalidFhirInput, JsonObject
from cdss.domain.medication_safety.medication_safety_contracts import unknown_fact

LOINC_EGFR = "98979-8"
LOINC_POTASSIUM = "6298-4"
LOINC_ACR = "9318-7"
LOINC_PROTEINURIA_24H = "2889-4"
LOINC_HEART_RATE = "8867-4"
LOINC_LVEF = "10230-1"
CLINICAL_FLAG_SYSTEM = "http://cdss.local/fhir/CodeSystem/clinical-flag"
READING_ROLE_EXTENSION = f"{EXT_BASE}/reading-role"
INPUT_EXTENSION_PREFIX = f"{EXT_BASE}/input/"

# Closed-world fields used by the seeded CDSS. Absence means false for this
# application profile; confirmed/refuted local Conditions can override it.
KNOWN_BOOLEAN_FLAGS = frozenset(
    {
        "is_pregnant",
        "has_coronary_artery_disease",
        "has_type_2_diabetes",
        "has_heart_failure",
        "has_ckd",
        "has_ckd_stage_3_or_higher",
        "has_diabetes",
        "has_cardiovascular_disease",
        "has_stroke",
        "has_tia",
        "has_frailty_syndrome",
        "has_target_organ_damage",
        "has_mi_acs",
        "has_ccs_angina",
        "has_ccs_revasc",
        "has_cabg",
        "has_hfref",
        "has_hfmref",
        "has_hfpef",
        "has_lvh",
        "has_kidney_transplant",
        "has_prior_creatinine_test",
        "still_using_ras_inhibitor",
        "creatinine_increased_over_30_percent",
        "tolerates_mra",
        "tolerates_spironolactone",
        "has_acute_ischemic_stroke",
        "is_thrombolysis_candidate",
        "has_acute_coronary_syndrome",
        "has_acute_cardiogenic_pulmonary_edema",
        "has_acute_aortic_syndrome",
        "has_eclampsia_severe_preeclampsia_or_hellp",
        "has_hypertensive_encephalopathy",
        "has_acute_intracerebral_hemorrhage",
        "has_tma_or_acute_kidney_injury",
        "has_pre_pregnancy_hypertension",
        "has_hypertension_before_week_20",
        "has_hypertension_after_week_20",
        "has_prior_gestational_hypertension",
        "has_high_preeclampsia_risk",
        "is_first_pregnancy",
        "has_multiple_pregnancy",
        "has_proteinuria",
        "has_autoimmune_disease",
        "has_severe_headache",
        "has_visual_disturbance",
        "has_epigastric_pain",
        "has_nausea_or_vomiting",
        "has_oliguria",
        "has_hemolysis",
        "has_elevated_liver_enzymes",
        "has_low_platelets",
        "has_seizure",
        "has_pulmonary_edema",
        "has_coagulopathy",
        "has_hypertensive_crisis",
        "is_treatment_target_not_achieved",
        "is_postpartum",
        "is_breastfeeding",
        "is_lifestyle_follow_up",
        "is_medication_follow_up",
        # Stateless medication follow-up gates. These are encoded as local
        # clinical-flag Conditions by the simulator, so they must be included
        # in this closed-world set to survive canonical Bundle parsing.
        "drug_replacement_required",
        "adherence_adequate",
        "dose_adequate",
        "has_asthma",
        "has_gout",
        "hypercalcaemia",
        "hypokalaemia",
        "angioedema_history",
        "renal_artery_stenosis",
        "active_bronchospasm",
        "pacemaker_present",
        "symptomatic_bradycardia",
        "metabolic_syndrome",
        "glucose_intolerance",
        "sinoatrial_block",
        "heart_failure_reduced_ef_nyha_3_or_4",
        "severe_leg_edema_history",
        "constipation",
        "acute_kidney_injury",
        "woman_of_childbearing_potential_not_using_contraception",
    }
)

SAFETY_FACT_KEYS = frozenset(
    {
        "pregnancy_status",
        "pregnancy_intention",
        "contraception_status",
        "breastfeeding_status",
        "serum_potassium",
        "eGFR",
        "acute_kidney_injury",
        "heart_rate",
        "heart_rhythm",
        "AV_block_grade",
        "pacemaker_present",
        "LVEF",
        "NYHA_class",
        "asthma_severity",
        "active_bronchospasm",
        "gout_status",
        "hypercalcaemia",
        "hypokalaemia",
        "angioedema_history",
        "renal_artery_stenosis",
        "athlete_status",
        "monitoring_plan",
        "metabolic_syndrome",
        "glucose_intolerance",
        "sinoatrial_block",
        "heart_failure_reduced_ef_nyha_3_or_4",
        "severe_leg_edema_history",
        "constipation",
        "woman_of_childbearing_potential_not_using_contraception",
        "is_pregnant",
        "is_breastfeeding",
        "is_postpartum",
    }
)

# Unlike ordinary diagnosis flags, omission of these workflow-quality flags
# means "not reported" and the follow-up policy deliberately defaults them to
# adequate. Do not collapse omission into False during canonical parsing.
OPTIONAL_DEFAULT_TRUE_FLAGS = frozenset({"adherence_adequate", "dose_adequate"})


@dataclass(frozen=True)
class ParsedClinicalBundle:
    raw_bundle: JsonObject
    runtime_input: JsonObject
    clinical_details: tuple[JsonObject, ...]
    trigger_evidence: tuple[JsonObject, ...]
    patient_id: str
    encounter_ids: tuple[str, ...]
    encounter_dates: tuple[str, ...]


def parse_clinical_bundle(bundle: Any) -> ParsedClinicalBundle:
    if not isinstance(bundle, Mapping) or bundle.get("resourceType") != "Bundle":
        _invalid("request body must be a FHIR Bundle (resourceType == 'Bundle')")
    entries = bundle.get("entry") or []
    if not isinstance(entries, list):
        _invalid("Bundle.entry must be an array")

    resources: list[Mapping[str, Any]] = []
    by_type: dict[str, list[Mapping[str, Any]]] = {}
    ids: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping) or not isinstance(entry.get("resource"), Mapping):
            _invalid(f"Bundle.entry[{index}] is missing resource")
        resource = entry["resource"]
        resource_type = resource.get("resourceType")
        if not isinstance(resource_type, str):
            _invalid(f"Bundle.entry[{index}].resource is missing resourceType")
        if resource_type == "Parameters":
            _invalid("Parameters resources are not part of the canonical clinical profile")
        resource_id = resource.get("id")
        if isinstance(resource_id, str):
            key = f"{resource_type}/{resource_id}"
            if key in ids:
                _invalid(f"duplicate resource id {key}")
            ids.add(key)
        resources.append(resource)
        by_type.setdefault(resource_type, []).append(resource)

    patients = by_type.get("Patient", [])
    if len(patients) != 1:
        _invalid("evaluation Bundle must contain exactly one Patient")
    patient = patients[0]
    patient_id = patient.get("id")
    if not isinstance(patient_id, str) or not patient_id:
        _invalid("Patient.id is required")
    patient_ref = f"Patient/{patient_id}"

    runtime: JsonObject = {
        key: False for key in KNOWN_BOOLEAN_FLAGS if key not in OPTIONAL_DEFAULT_TRUE_FLAGS
    }
    runtime["clinical_facts"] = {key: unknown_fact() for key in SAFETY_FACT_KEYS}
    runtime["active_medication_regimen"] = []
    runtime["facility_capability"] = "FULL_RESOURCES"
    runtime["risk_factor_count"] = 0
    _apply_birth_date(patient, runtime)
    _apply_extensions(patient, runtime)

    details: list[JsonObject] = []
    _apply_conditions(by_type.get("Condition", []), patient_ref, runtime, details)

    # Traversal checkpoints may enrich a bundle with a flat boolean mirror
    # while preserving the canonical Condition resource.  Accept that mirror
    # on re-evaluation as a compatibility path; the Condition remains the
    # authoritative FHIR representation for normal requests.
    for key in KNOWN_BOOLEAN_FLAGS:
        mirrored = bundle.get(key)
        if isinstance(mirrored, bool):
            runtime[key] = mirrored
            _record_fact(runtime, key, mirrored, source_reference="Bundle")

    encounters = by_type.get("Encounter", [])
    encounter_dates: dict[str, str] = {}
    for encounter in encounters:
        _require_subject(encounter, patient_ref)
        encounter_id = encounter.get("id")
        started = (
            (encounter.get("period") or {}).get("start")
            if isinstance(encounter.get("period"), Mapping)
            else None
        )
        if not isinstance(encounter_id, str) or not isinstance(started, str):
            _invalid("Encounter.id and Encounter.period.start are required")
        _parse_date(started, f"Encounter/{encounter_id}.period.start")
        encounter_dates[encounter_id] = started

    ordered = sorted(encounter_dates.items(), key=lambda item: item[1])
    if len(ordered) > 1 and ordered[-1][1] == ordered[-2][1]:
        _invalid("latest Encounter date is ambiguous")
    observations = by_type.get("Observation", [])
    bp_by_encounter: dict[str | None, dict[str, tuple[float | int, Mapping[str, Any]]]] = {}
    bp_by_role: dict[str, dict[str, tuple[float | int, Mapping[str, Any]]]] = {}
    labs: list[JsonObject] = []
    home_bp: dict[str, float | int] = {}
    for observation in observations:
        _require_subject(observation, patient_ref)
        code = _first_code(observation)
        value = _quantity_value(observation)
        encounter_id = (
            _reference_id((observation.get("encounter") or {}).get("reference"))
            if isinstance(observation.get("encounter"), Mapping)
            else None
        )
        if encounter_id is not None and encounter_id not in encounter_dates:
            _invalid(f"Observation references unknown Encounter/{encounter_id}")
        role = _extension_value(observation.get("extension"), READING_ROLE_EXTENSION)
        if code in {LOINC_SBP_CODE, LOINC_DBP_CODE}:
            if value is None:
                _invalid(
                    "blood-pressure Observation "
                    f"{observation.get('id', '<unknown>')} has no numeric value"
                )
            side = "sbp" if code == LOINC_SBP_CODE else "dbp"
            if role == "home":
                if side in home_bp and home_bp[side] != value:
                    _invalid(f"conflicting home {side} values")
                home_bp[side] = value
                continue
            if encounter_id is None and role in {"current_clinic", "previous"}:
                role_bucket = bp_by_role.setdefault(role, {})
                if side in role_bucket and role_bucket[side][0] != value:
                    _invalid(f"conflicting {role} {side} values")
                role_bucket[side] = (value, observation)
                continue
            bucket = bp_by_encounter.setdefault(encounter_id, {})
            if side in bucket and bucket[side][0] != value:
                _invalid(f"conflicting {side} values for Encounter/{encounter_id or 'snapshot'}")
            bucket[side] = (value, observation)
        elif (
            code
            in {
                LOINC_EGFR,
                LOINC_POTASSIUM,
                LOINC_ACR,
                LOINC_PROTEINURIA_24H,
                LOINC_HEART_RATE,
                LOINC_LVEF,
            }
            and value is not None
        ):
            label_en, label_vi, runtime_key = _lab_metadata(code)
            item: JsonObject = {
                "id": str(observation.get("id") or f"lab-{len(labs)}"),
                "category": "laboratory",
                "label_en": label_en,
                "label_vi": label_vi,
                "value": value,
                "unit": str((observation.get("valueQuantity") or {}).get("unit") or ""),
                "effective_date_time": observation.get("effectiveDateTime"),
                "source_reference": f"Observation/{observation.get('id')}"
                if observation.get("id")
                else None,
            }
            labs.append(item)
            if runtime_key:
                runtime[runtime_key] = value
                _record_fact(
                    runtime,
                    runtime_key,
                    value,
                    source_reference=item["source_reference"],
                    effective_time=item["effective_date_time"],
                )

    if encounters:
        if None in bp_by_encounter:
            _invalid("BP Observations in a longitudinal Bundle must reference an Encounter")
        latest_id = ordered[-1][0]
        _apply_bp_pair(bp_by_encounter.get(latest_id), runtime, "current_clinic")
        latest_encounter = next(e for e in encounters if e.get("id") == latest_id)
        _apply_extensions(latest_encounter, runtime)
        if len(ordered) > 1:
            previous_id = ordered[-2][0]
            _apply_bp_pair(bp_by_encounter.get(previous_id), runtime, "previous")
            details.extend(
                [
                    {
                        "id": "previous-sbp",
                        "category": "previous_reading",
                        "label_en": "Previous systolic blood pressure",
                        "label_vi": "Huyết áp tâm thu lần trước",
                        "value": runtime["previous_sbp"],
                        "unit": "mmHg",
                        "effective_date_time": encounter_dates[previous_id],
                        "source_reference": f"Encounter/{previous_id}",
                    },
                    {
                        "id": "previous-dbp",
                        "category": "previous_reading",
                        "label_en": "Previous diastolic blood pressure",
                        "label_vi": "Huyết áp tâm trương lần trước",
                        "value": runtime["previous_dbp"],
                        "unit": "mmHg",
                        "effective_date_time": encounter_dates[previous_id],
                        "source_reference": f"Encounter/{previous_id}",
                    },
                ]
            )
        for encounter_id, started in ordered:
            details.append(
                {
                    "id": f"encounter-{encounter_id}",
                    "category": "historical_encounter",
                    "label_en": "Encounter",
                    "label_vi": "Lần khám",
                    "value": started,
                    "source_reference": f"Encounter/{encounter_id}",
                }
            )
    else:
        if any(key is not None for key in bp_by_encounter):
            _invalid("Observation references an Encounter that is not present")
        if bp_by_role:
            for role, bucket in bp_by_role.items():
                _apply_bp_pair(bucket, runtime, role)
            if "current_clinic" not in bp_by_role:
                _invalid("snapshot requires current_clinic blood pressure")
        else:
            _apply_bp_pair(bp_by_encounter.get(None), runtime, "current_clinic")

    if home_bp:
        if set(home_bp) != {"sbp", "dbp"}:
            _invalid("home blood pressure requires both systolic and diastolic values")
        runtime["home_sbp"], runtime["home_dbp"] = home_bp["sbp"], home_bp["dbp"]

    trigger = _current_bp_evidence(runtime)
    details.extend(labs)
    runtime["active_medication_regimen"] = [
        *_apply_medications(
            by_type.get("MedicationRequest", []),
            patient_ref,
            encounter_dates,
            details,
            resource_type="MedicationRequest",
        ),
        *_apply_medications(
            by_type.get("MedicationStatement", []),
            patient_ref,
            encounter_dates,
            details,
            resource_type="MedicationStatement",
        ),
    ]
    declared_follow_up_number = runtime.get("pregnancy_follow_up_number")
    derived_follow_up_number = max(0, len(ordered) - 1)
    if declared_follow_up_number is not None and (
        not isinstance(declared_follow_up_number, int)
        or isinstance(declared_follow_up_number, bool)
        or declared_follow_up_number < 0
        or declared_follow_up_number != derived_follow_up_number
    ):
        _invalid(
            "pregnancy_follow_up_number must be a non-negative integer matching "
            "the number of prior Encounters"
        )

    return ParsedClinicalBundle(
        deepcopy(dict(bundle)),
        runtime,
        tuple(details),
        tuple(trigger),
        patient_id,
        tuple(encounter_id for encounter_id, _ in ordered),
        tuple(started for _, started in ordered),
    )


def _apply_bp_pair(
    bucket: Mapping[str, tuple[float | int, Mapping[str, Any]]] | None,
    runtime: JsonObject,
    prefix: str,
) -> None:
    if bucket is None or set(bucket) != {"sbp", "dbp"}:
        _invalid(f"{prefix} blood pressure requires one systolic and one diastolic Observation")
    runtime[f"{prefix}_sbp"] = bucket["sbp"][0]
    runtime[f"{prefix}_dbp"] = bucket["dbp"][0]


def _apply_birth_date(patient: Mapping[str, Any], runtime: JsonObject) -> None:
    value = patient.get("birthDate")
    if not isinstance(value, str):
        return
    birth = _parse_date(value[:10], "Patient.birthDate")
    today = datetime.now(UTC).date()
    runtime["age"] = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _apply_extensions(resource: Mapping[str, Any], runtime: JsonObject) -> None:
    extensions = resource.get("extension") or []
    risk = _extension_value(extensions, EXT_RISK_FACTOR_COUNT)
    facility = _extension_value(extensions, EXT_FACILITY_CAPABILITY)
    if isinstance(risk, int) and not isinstance(risk, bool):
        runtime["risk_factor_count"] = risk
    if facility in {"FULL_RESOURCES", "LIMITED_RESOURCES"}:
        runtime["facility_capability"] = facility
    for extension in extensions if isinstance(extensions, list) else []:
        if not isinstance(extension, Mapping) or not isinstance(extension.get("url"), str):
            continue
        url = extension["url"]
        if not url.startswith(INPUT_EXTENSION_PREFIX):
            continue
        key = url.removeprefix(INPUT_EXTENSION_PREFIX)
        value = _typed_extension_value(extension)
        if value is not None:
            runtime[key] = value
            if key in SAFETY_FACT_KEYS:
                _record_fact(runtime, key, value, source_reference=url, source="manual")


def _apply_conditions(
    conditions: list[Mapping[str, Any]],
    patient_ref: str,
    runtime: JsonObject,
    details: list[JsonObject],
) -> None:
    for condition in conditions:
        _require_subject(condition, patient_ref)
        code_concept = condition.get("code")
        codings = (code_concept or {}).get("coding") if isinstance(code_concept, Mapping) else []
        codings = codings if isinstance(codings, list) else []
        pairs = {(c.get("system"), c.get("code")) for c in codings if isinstance(c, Mapping)}
        verification = _coding_codes(
            condition.get("verificationStatus"),
            "http://terminology.hl7.org/CodeSystem/condition-ver-status",
        )
        active = "refuted" not in verification
        for system, code in pairs:
            if (
                system == CLINICAL_FLAG_SYSTEM
                and isinstance(code, str)
                and code in KNOWN_BOOLEAN_FLAGS
            ):
                runtime[code] = active
                _record_fact(
                    runtime,
                    code,
                    active,
                    source_reference=f"Condition/{condition.get('id')}"
                    if condition.get("id")
                    else "Condition",
                )
                fact_key = {
                    "is_pregnant": "pregnancy_status",
                    "is_breastfeeding": "breastfeeding_status",
                    "is_postpartum": "is_postpartum",
                    "has_gout": "gout_status",
                }.get(code)
                if fact_key:
                    _record_fact(
                        runtime,
                        fact_key,
                        active,
                        source_reference=f"Condition/{condition.get('id')}"
                        if condition.get("id")
                        else "Condition",
                    )
        codes = {str(code) for _, code in pairs if code is not None}
        if any(code == "E11" or code.startswith("E11.") for code in codes) or "44054006" in codes:
            runtime["has_type_2_diabetes"] = runtime["has_diabetes"] = active
        if any(code == "N18" or code.startswith("N18.") for code in codes) or "709044004" in codes:
            runtime["has_ckd"] = active
        if (
            any(code.startswith(("N18.3", "N18.4", "N18.5", "N18.6")) for code in codes)
            or "433144002" in codes
        ):
            runtime["has_ckd"] = runtime["has_ckd_stage_3_or_higher"] = active
        if any(code.startswith("I25") for code in codes) or "53741008" in codes:
            runtime["has_coronary_artery_disease"] = active
        text = (code_concept or {}).get("text") if isinstance(code_concept, Mapping) else None
        details.append(
            {
                "id": str(condition.get("id") or f"condition-{len(details)}"),
                "category": "condition",
                "label_en": "Condition",
                "label_vi": "Chẩn đoán",
                "value": str(text or ", ".join(sorted(codes))),
                "source_reference": f"Condition/{condition.get('id')}"
                if condition.get("id")
                else None,
            }
        )


def _apply_medications(
    medications: list[Mapping[str, Any]],
    patient_ref: str,
    encounter_dates: Mapping[str, str],
    details: list[JsonObject],
    *,
    resource_type: str,
) -> list[JsonObject]:
    active_regimen: list[JsonObject] = []
    for medication in medications:
        _require_subject(medication, patient_ref)
        encounter_id = (
            _reference_id((medication.get("encounter") or {}).get("reference"))
            if isinstance(medication.get("encounter"), Mapping)
            else None
        )
        if encounter_id is not None and encounter_id not in encounter_dates:
            _invalid(f"MedicationRequest references unknown Encounter/{encounter_id}")
        concept = medication.get("medicationCodeableConcept") or {}
        name = _medication_name(concept)
        dose = None
        instructions = medication.get("dosageInstruction") or []
        if instructions and isinstance(instructions[0], Mapping):
            rates = instructions[0].get("doseAndRate") or []
            if rates and isinstance(rates[0], Mapping):
                dose = rates[0].get("doseQuantity")
        value = str(name or "Medication")
        if isinstance(dose, Mapping) and dose.get("value") is not None:
            value += f" {dose['value']} {dose.get('unit', '')}".rstrip()
        effective_time = (
            medication.get("authoredOn")
            or medication.get("effectiveDateTime")
            or (
                (medication.get("effectivePeriod") or {}).get("start")
                if isinstance(medication.get("effectivePeriod"), Mapping)
                else None
            )
            or (encounter_dates.get(encounter_id) if encounter_id else None)
        )
        details.append(
            {
                "id": str(medication.get("id") or f"medication-{len(details)}"),
                "category": "medication",
                "label_en": "Medication",
                "label_vi": "Thuốc đang dùng",
                "value": value,
                "effective_date_time": effective_time,
                "source_reference": f"{resource_type}/{medication.get('id')}"
                if medication.get("id")
                else None,
            }
        )
        status = medication.get("status")
        if status not in {"completed", "stopped", "cancelled", "entered-in-error"}:
            active_regimen.append(
                {
                    "id": str(medication.get("id") or f"medication-{len(active_regimen)}"),
                    "name": name or value,
                    "code": _medication_code(concept),
                    "status": status or "active",
                    "effective_time": effective_time,
                    "source_reference": f"{resource_type}/{medication.get('id')}"
                    if medication.get("id")
                    else None,
                }
            )
    return active_regimen


def _medication_code(concept: object) -> str | None:
    if not isinstance(concept, Mapping):
        return None
    codings = concept.get("coding")
    if not isinstance(codings, list):
        return None
    for coding in codings:
        if isinstance(coding, Mapping) and isinstance(coding.get("code"), str):
            return coding["code"]
    return None


def _medication_name(concept: object) -> str | None:
    if not isinstance(concept, Mapping):
        return None
    text = concept.get("text")
    if isinstance(text, str) and text:
        return text
    codings = concept.get("coding")
    if isinstance(codings, list):
        for coding in codings:
            if isinstance(coding, Mapping):
                display = coding.get("display")
                if isinstance(display, str) and display:
                    return display
    return None


def _current_bp_evidence(runtime: Mapping[str, Any]) -> list[JsonObject]:
    return [
        {
            "id": "current-sbp",
            "label_en": "Current systolic blood pressure",
            "label_vi": "Huyết áp tâm thu hiện tại",
            "value": runtime["current_clinic_sbp"],
            "unit": "mmHg",
        },
        {
            "id": "current-dbp",
            "label_en": "Current diastolic blood pressure",
            "label_vi": "Huyết áp tâm trương hiện tại",
            "value": runtime["current_clinic_dbp"],
            "unit": "mmHg",
        },
    ]


def _lab_metadata(code: str) -> tuple[str, str, str | None]:
    return {
        LOINC_EGFR: ("eGFR", "eGFR", "eGFR"),
        LOINC_POTASSIUM: ("Potassium", "Kali", "serum_potassium"),
        LOINC_ACR: (
            "Urine albumin/creatinine ratio",
            "Tỷ số albumin/creatinin niệu",
            "acr_mg_mmol",
        ),
        LOINC_PROTEINURIA_24H: (
            "24-hour urine protein",
            "Protein niệu 24 giờ",
            "proteinuria_24h_mg",
        ),
        LOINC_HEART_RATE: ("Heart rate", "Nhịp tim", "heart_rate"),
        LOINC_LVEF: (
            "Left ventricular ejection fraction",
            "Phân suất tống máu thất trái",
            "LVEF",
        ),
    }[code]


def _record_fact(
    runtime: JsonObject,
    key: str,
    value: object,
    *,
    source_reference: str | None = None,
    effective_time: object = None,
    source: str = "FHIR",
) -> None:
    if key not in SAFETY_FACT_KEYS and key not in KNOWN_BOOLEAN_FLAGS:
        return
    facts = runtime.setdefault("clinical_facts", {})
    if not isinstance(facts, dict):
        return
    if isinstance(value, Mapping) and value.get("status") in {
        "present",
        "absent",
        "unknown",
        "conflicting",
    }:
        status = value["status"]
        normalized_value = value.get("value")
    elif isinstance(value, str) and value.casefold() in {
        "present",
        "absent",
        "unknown",
        "conflicting",
    }:
        status = value.casefold()
        normalized_value = None
    elif isinstance(value, bool):
        status = "present" if value else "absent"
        normalized_value = value
    else:
        status = "present" if value is not None else "unknown"
        normalized_value = value
    evidence: JsonObject = {"source": source}
    if source_reference:
        evidence["source"] = source_reference
    if effective_time is not None:
        evidence["effective_time"] = effective_time
    previous = facts.get(key)
    previous_status = previous.get("status") if isinstance(previous, Mapping) else "unknown"
    previous_value = previous.get("value") if isinstance(previous, Mapping) else None
    if previous_status not in {"unknown", status} and not (
        previous_status == "present" and status == "present" and previous_value == normalized_value
    ):
        facts[key] = {"status": "conflicting", "evidence": _fact_evidence(previous, evidence)}
        return
    if previous_status == "present" and previous_value != normalized_value:
        facts[key] = {"status": "conflicting", "evidence": _fact_evidence(previous, evidence)}
        return
    existing_evidence = previous.get("evidence", []) if isinstance(previous, Mapping) else []
    facts[key] = {
        "status": status,
        "value": normalized_value,
        "evidence": [*existing_evidence, evidence]
        if isinstance(existing_evidence, list)
        else [evidence],
    }


def _fact_evidence(previous: object, current: JsonObject) -> list[JsonObject]:
    prior = previous.get("evidence", []) if isinstance(previous, Mapping) else []
    return [*(prior if isinstance(prior, list) else []), current]


def _require_subject(resource: Mapping[str, Any], patient_ref: str) -> None:
    subject = resource.get("subject")
    reference = subject.get("reference") if isinstance(subject, Mapping) else None
    if reference != patient_ref:
        _invalid(f"{resource.get('resourceType')} references unknown patient {reference!r}")


def _first_code(resource: Mapping[str, Any]) -> str | None:
    concept = resource.get("code")
    codings = concept.get("coding") if isinstance(concept, Mapping) else None
    if not isinstance(codings, list):
        return None
    for coding in codings:
        if (
            isinstance(coding, Mapping)
            and coding.get("system") == "http://loinc.org"
            and isinstance(coding.get("code"), str)
        ):
            return coding["code"]
    return None


def _coding_codes(concept: Any, system: str) -> set[str]:
    if not isinstance(concept, Mapping):
        return set()
    return {
        str(c["code"])
        for c in concept.get("coding") or []
        if isinstance(c, Mapping) and c.get("system") == system and c.get("code") is not None
    }


def _quantity_value(resource: Mapping[str, Any]) -> float | int | None:
    quantity = resource.get("valueQuantity")
    value = quantity.get("value") if isinstance(quantity, Mapping) else None
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _reference_id(reference: Any) -> str | None:
    return reference.rsplit("/", 1)[-1] if isinstance(reference, str) and "/" in reference else None


def _extension_value(extensions: Any, url: str) -> Any:
    if not isinstance(extensions, list):
        return None
    for extension in extensions:
        if isinstance(extension, Mapping) and extension.get("url") == url:
            return _typed_extension_value(extension)
    return None


def _typed_extension_value(extension: Mapping[str, Any]) -> Any:
    for key in (
        "valueBoolean",
        "valueInteger",
        "valueDecimal",
        "valueString",
        "valueCode",
        "valueDate",
    ):
        if key in extension:
            return extension[key]
    return None


def _parse_date(value: str, path: str) -> date:
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise InvalidFhirInput(
            details={"reason": f"{path} is not a valid date: {value!r}"}
        ) from exc


def _invalid(reason: str) -> Never:
    raise InvalidFhirInput(details={"reason": reason})
