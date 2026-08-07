"""Convert an HL7 FHIR R4 input `Bundle` into the flat runtime `input` object
the decision-tree engine consumes (`walk_tree`'s second argument), and back.

The engine's `input.*` namespace (frozen per tree in
`docs/cdss/context-contract.md`) is a flat bag of ~90 ad-hoc keys accumulated
across 13 seeded trees: numeric vitals (a handful of distinct blood-pressure
"reading roles" -- current clinic, previous visit, the single diagnostic
clinic reading), boolean clinical flags (comorbidities, presenting symptoms,
pregnancy status), and a long tail of workflow/orchestration state (follow-up
stage, facility capability, caller-supplied BP targets, medication-review
flags) that has no real-world clinical meaning outside this CDSS.

Rather than force all of that through one resource shape, each key is routed
to the FHIR R4 resource that actually fits its meaning:

- `Patient.birthDate` -> `age` (computed in years as of today).
- `Observation` (LOINC-coded, vital-signs/laboratory category) -> numeric
  vitals and labs. Blood-pressure "reading role" (which of the BP fields a
  reading belongs to) has no standard FHIR vocabulary, so it rides along as a
  local extension, the same pattern this codebase's PlanDefinition export
  already uses for its own `cdss.local` extensions.
- `Condition` (local `clinical-flag` CodeSystem, `verificationStatus`
  confirmed/refuted) -> boolean diagnosis/symptom/status flags (`has_*`,
  `is_*`). A local code system is used deliberately instead of guessing
  SNOMED CT/ICD-10 codes for ~45 flags: it is verifiably correct (this module
  defines it), and a real integration can still add a second `coding` from a
  standard system to the same `CodeableConcept` for interop without this
  mapper depending on it.
- `Parameters` -> everything else: workflow/orchestration state that isn't a
  clinical resource at all (`facility_capability`, `active_bp_target`,
  `contraindicated_drug_classes`, ...), plus any key this module doesn't know
  about yet, so no input field is ever silently dropped. Nested
  objects/arrays are encoded via `Parameters.parameter.part` (arrays are
  marked with a boolean extension since repeated-name and single-element
  arrays would otherwise be ambiguous).

`bundle_to_input` is intentionally permissive about resource types it does not
recognise (ignored, for forward compatibility with richer real-world bundles)
but strict about malformed FHIR shape it must act on (raises
`InvalidFhirInput`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from cdss.domain.decision_tree import InvalidFhirInput
from cdss.domain.decision_tree.contracts import JsonObject, JsonValue

_EXT_BASE = "http://cdss.local/fhir/StructureDefinition"
_EXT_READING_ROLE = f"{_EXT_BASE}/reading-role"
_EXT_PARAMETER_IS_ARRAY = f"{_EXT_BASE}/parameter-is-array"

_CS_CLINICAL_FLAG = "http://cdss.local/fhir/CodeSystem/clinical-flag"
_CS_OBSERVATION_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
_CS_CONDITION_CLINICAL = "http://terminology.hl7.org/CodeSystem/condition-clinical"
_CS_CONDITION_VER_STATUS = "http://terminology.hl7.org/CodeSystem/condition-ver-status"

_LOINC = "http://loinc.org"
_LOINC_BP_PANEL = "85354-9"
_LOINC_SBP = "8480-6"
_LOINC_DBP = "8462-4"

_ARRAY_ITEM_NAME = "item"

# reading role -> (systolic input key, diastolic input key). All roles share
# the same LOINC-coded BP panel/components; the role is this CDSS's own
# follow-up-workflow distinction (e.g. "the most recent previous visit's
# reading" vs "today's clinic reading"), not a standard FHIR concept.
_BP_READING_ROLES: dict[str, tuple[str, str]] = {
    "current_clinic": ("current_clinic_sbp", "current_clinic_dbp"),
    "previous_visit": ("previous_sbp", "previous_dbp"),
    "clinic_1": ("clinic_1_sbp", "clinic_1_dbp"),
}

# Non-BP lab-value Observations. LOINC codes are a best effort and have not
# been checked against a live terminology server -- verify before relying on
# them for real EHR interop.
_LAB_OBSERVATIONS: dict[str, tuple[str, str, str]] = {
    # key -> (loinc_code, display, unit)
    "acr_mg_mmol": ("9318-7", "Albumin/Creatinine [Ratio] in Urine", "mg/mmol"),
    "proteinuria_24h_mg": ("2889-4", "Protein [Mass/time] in 24 hour Urine", "mg"),
}

# has_*/is_* keys that are workflow/orchestration/derived-assessment state
# rather than a clinical diagnosis, symptom, or status -- these do not belong
# on a Condition resource and are carried as plain Parameters instead.
_WORKFLOW_FLAG_KEYS = frozenset(
    {
        "is_medication_follow_up",
        "is_lifestyle_follow_up",
        "is_treatment_target_not_achieved",
        "is_thrombolysis_candidate",
        "has_dosage_adjustment_request",
        "has_duplicate_drug_class",
        "has_duplicate_ras_inhibitor",
        "has_prior_creatinine_test",
        "has_prior_prescription",
    }
)


def is_clinical_flag_key(key: str) -> bool:
    """True if `key` is a boolean clinical Condition flag (as opposed to
    workflow/orchestration state that happens to share the has_/is_ prefix).
    """

    return key.startswith(("has_", "is_")) and key not in _WORKFLOW_FLAG_KEYS


# --- Bundle -> flat input ------------------------------------------------


def bundle_to_input(bundle: Any) -> JsonObject:
    """Convert a FHIR R4 `Bundle` (as a parsed JSON dict) into the flat
    `input.*` object the decision-tree engine consumes."""

    if not isinstance(bundle, Mapping) or bundle.get("resourceType") != "Bundle":
        raise InvalidFhirInput(
            details={"reason": "request input must be a FHIR Bundle (resourceType == 'Bundle')"}
        )

    flat: JsonObject = {}
    parameter_entries: list[Mapping[str, Any]] = []

    for entry in bundle.get("entry") or []:
        if not isinstance(entry, Mapping):
            raise InvalidFhirInput(details={"reason": "Bundle.entry item is not an object"})
        resource = entry.get("resource")
        if not isinstance(resource, Mapping):
            raise InvalidFhirInput(details={"reason": "Bundle.entry is missing 'resource'"})

        resource_type = resource.get("resourceType")
        if resource_type == "Patient":
            _apply_patient(resource, flat)
        elif resource_type == "Observation":
            _apply_observation(resource, flat)
        elif resource_type == "Condition":
            _apply_condition(resource, flat)
        elif resource_type == "Parameters":
            for parameter in resource.get("parameter") or []:
                if not isinstance(parameter, Mapping):
                    raise InvalidFhirInput(
                        details={"reason": "Parameters.parameter item is not an object"}
                    )
                parameter_entries.append(parameter)
        # Unrecognized resource types are ignored: forward-compatible with
        # bundles carrying additional clinical context this mapper doesn't
        # use (yet).

    for parameter in parameter_entries:
        name = parameter.get("name")
        if not isinstance(name, str):
            raise InvalidFhirInput(details={"reason": "Parameters.parameter is missing 'name'"})
        flat[name] = _parameter_to_value(parameter)

    return flat


def _apply_patient(resource: Mapping[str, Any], flat: JsonObject) -> None:
    birth_date = resource.get("birthDate")
    if not isinstance(birth_date, str):
        return
    try:
        birth = date.fromisoformat(birth_date[:10])
    except ValueError as exc:
        raise InvalidFhirInput(
            details={"reason": f"Patient.birthDate is not a valid date: {birth_date!r}"}
        ) from exc
    today = datetime.now(UTC).date()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    flat["age"] = age


def _apply_observation(resource: Mapping[str, Any], flat: JsonObject) -> None:
    components = resource.get("component") or []
    has_bp_component = any(
        _LOINC_SBP in (codes := _codings(component.get("code")).get(_LOINC, set()))
        or _LOINC_DBP in codes
        for component in components
        if isinstance(component, Mapping)
    )
    if has_bp_component:
        _apply_bp_observation(resource, components, flat)
        return

    codes = _codings(resource.get("code")).get(_LOINC, set())
    for key, (loinc_code, _display, _unit) in _LAB_OBSERVATIONS.items():
        if loinc_code in codes:
            value = _quantity_value(resource.get("valueQuantity"))
            if value is not None:
                flat[key] = value
            return


def _apply_bp_observation(
    resource: Mapping[str, Any],
    components: Sequence[Any],
    flat: JsonObject,
) -> None:
    role = _reading_role(resource)
    if role not in _BP_READING_ROLES:
        raise InvalidFhirInput(
            details={
                "reason": (
                    "blood-pressure Observation is missing a recognized "
                    f"'{_EXT_READING_ROLE}' extension"
                )
            }
        )
    sbp_key, dbp_key = _BP_READING_ROLES[role]
    for component in components:
        if not isinstance(component, Mapping):
            continue
        component_codes = _codings(component.get("code")).get(_LOINC, set())
        value = _quantity_value(component.get("valueQuantity"))
        if value is None:
            continue
        if _LOINC_SBP in component_codes:
            flat[sbp_key] = value
        elif _LOINC_DBP in component_codes:
            flat[dbp_key] = value


def _apply_condition(resource: Mapping[str, Any], flat: JsonObject) -> None:
    codes = _codings(resource.get("code")).get(_CS_CLINICAL_FLAG, set())
    if not codes:
        return
    verification = _codings(resource.get("verificationStatus")).get(_CS_CONDITION_VER_STATUS, set())
    value = "refuted" not in verification
    for key in codes:
        flat[key] = value


def _codings(codeable_concept: Any) -> dict[str, set[str]]:
    if not isinstance(codeable_concept, Mapping):
        return {}
    result: dict[str, set[str]] = {}
    for coding in codeable_concept.get("coding") or []:
        if not isinstance(coding, Mapping):
            continue
        system, code = coding.get("system"), coding.get("code")
        if isinstance(system, str) and isinstance(code, str):
            result.setdefault(system, set()).add(code)
    return result


def _quantity_value(quantity: Any) -> float | int | None:
    if not isinstance(quantity, Mapping):
        return None
    value = quantity.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _find_extension(container: Mapping[str, Any], url: str) -> Mapping[str, Any] | None:
    for extension in container.get("extension") or []:
        if isinstance(extension, Mapping) and extension.get("url") == url:
            return extension
    return None


def _reading_role(resource: Mapping[str, Any]) -> str | None:
    extension = _find_extension(resource, _EXT_READING_ROLE)
    if extension is None:
        return None
    value = extension.get("valueCode") or extension.get("valueString")
    return value if isinstance(value, str) else None


# --- Parameters <-> JSON value codec --------------------------------------
#
# A dict becomes one Parameters.parameter with one `part` per key (part names
# are the dict's own keys). A list becomes one Parameters.parameter marked
# with the parameter-is-array extension, with one `part` per element (all
# named "item"); the marker disambiguates a single-element array from a
# scalar, which repeated-name-or-part-name conventions alone cannot.


def _value_to_parameter(name: str, value: JsonValue) -> JsonObject:
    if isinstance(value, Mapping):
        return {
            "name": name,
            "part": [_value_to_parameter(key, item) for key, item in value.items()],
        }
    if isinstance(value, list):
        return {
            "name": name,
            "extension": [{"url": _EXT_PARAMETER_IS_ARRAY, "valueBoolean": True}],
            "part": [_value_to_parameter(_ARRAY_ITEM_NAME, item) for item in value],
        }
    return {"name": name, **_scalar_parameter_value(value)}


def _scalar_parameter_value(value: JsonValue) -> JsonObject:
    if isinstance(value, bool):
        return {"valueBoolean": value}
    if isinstance(value, int):
        return {"valueInteger": value}
    if isinstance(value, float):
        return {"valueDecimal": value}
    if isinstance(value, str):
        return {"valueString": value}
    if value is None:
        return {}
    raise InvalidFhirInput(
        details={
            "reason": f"unsupported input value type for FHIR Parameters: {type(value).__name__}"
        }
    )


_SCALAR_VALUE_KEYS = ("valueBoolean", "valueInteger", "valueDecimal", "valueString")


def _parameter_to_value(entry: Mapping[str, Any]) -> JsonValue:
    if _find_extension(entry, _EXT_PARAMETER_IS_ARRAY) is not None:
        return [
            _parameter_to_value(part)
            for part in entry.get("part") or []
            if isinstance(part, Mapping)
        ]
    parts = entry.get("part")
    if parts is not None:
        result: JsonObject = {}
        for part in parts:
            if not isinstance(part, Mapping) or not isinstance(part.get("name"), str):
                raise InvalidFhirInput(details={"reason": "Parameters part is missing 'name'"})
            result[part["name"]] = _parameter_to_value(part)
        return result
    for key in _SCALAR_VALUE_KEYS:
        if key in entry:
            return entry[key]
    return None


# --- flat input -> Bundle (reference/reverse mapping, used by tests and as
# a worked example for real callers constructing request bodies) ----------


def input_to_bundle(flat: Mapping[str, JsonValue]) -> JsonObject:
    """Reverse of `bundle_to_input`: build a FHIR Bundle from a flat
    `input.*` object. Exists so tests (and integrators) don't have to
    hand-write FHIR resources for every field."""

    remaining = dict(flat)
    entries: list[JsonObject] = []

    age = remaining.pop("age", None)
    if age is not None:
        entries.append({"resource": _patient_resource(age)})

    for role, (sbp_key, dbp_key) in _BP_READING_ROLES.items():
        sbp = remaining.pop(sbp_key, None)
        dbp = remaining.pop(dbp_key, None)
        if sbp is None and dbp is None:
            continue
        entries.append({"resource": _bp_observation_resource(role, sbp, dbp)})

    for key, (loinc_code, display, unit) in _LAB_OBSERVATIONS.items():
        value = remaining.pop(key, None)
        if value is not None:
            entries.append(
                {"resource": _lab_observation_resource(loinc_code, display, unit, value)}
            )

    for key in [k for k in remaining if is_clinical_flag_key(k)]:
        value = remaining.pop(key)
        if not isinstance(value, bool):
            raise InvalidFhirInput(details={"reason": f"'{key}' must be a boolean, got {value!r}"})
        entries.append({"resource": _condition_resource(key, value)})

    if remaining:
        entries.append(
            {
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": [
                        _value_to_parameter(key, value) for key, value in remaining.items()
                    ],
                }
            }
        )

    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def _patient_resource(age: JsonValue) -> JsonObject:
    if not isinstance(age, int) or isinstance(age, bool):
        raise InvalidFhirInput(details={"reason": f"'age' must be an integer, got {age!r}"})
    birth_year = datetime.now(UTC).date().year - age
    return {"resourceType": "Patient", "birthDate": date(birth_year, 1, 1).isoformat()}


def _bp_observation_resource(role: str, sbp: JsonValue, dbp: JsonValue) -> JsonObject:
    components = []
    if sbp is not None:
        components.append(
            {
                "code": {
                    "coding": [
                        {"system": _LOINC, "code": _LOINC_SBP, "display": "Systolic blood pressure"}
                    ]
                },
                "valueQuantity": {"value": sbp, "unit": "mmHg"},
            }
        )
    if dbp is not None:
        components.append(
            {
                "code": {
                    "coding": [
                        {
                            "system": _LOINC,
                            "code": _LOINC_DBP,
                            "display": "Diastolic blood pressure",
                        }
                    ]
                },
                "valueQuantity": {"value": dbp, "unit": "mmHg"},
            }
        )
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": _CS_OBSERVATION_CATEGORY, "code": "vital-signs"}]}],
        "code": {
            "coding": [
                {"system": _LOINC, "code": _LOINC_BP_PANEL, "display": "Blood pressure panel"}
            ]
        },
        "extension": [{"url": _EXT_READING_ROLE, "valueCode": role}],
        "component": components,
    }


def _lab_observation_resource(
    loinc_code: str, display: str, unit: str, value: JsonValue
) -> JsonObject:
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": _CS_OBSERVATION_CATEGORY, "code": "laboratory"}]}],
        "code": {"coding": [{"system": _LOINC, "code": loinc_code, "display": display}]},
        "valueQuantity": {"value": value, "unit": unit},
    }


def _condition_resource(key: str, value: bool) -> JsonObject:
    return {
        "resourceType": "Condition",
        "clinicalStatus": {
            "coding": [
                {"system": _CS_CONDITION_CLINICAL, "code": "active" if value else "resolved"}
            ]
        },
        "verificationStatus": {
            "coding": [
                {"system": _CS_CONDITION_VER_STATUS, "code": "confirmed" if value else "refuted"}
            ]
        },
        "code": {"coding": [{"system": _CS_CLINICAL_FLAG, "code": key}]},
    }
