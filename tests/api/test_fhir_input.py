"""Unit tests for the HL7 FHIR R4 input Bundle <-> flat runtime-input mapping."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cdss.api.schemas.fhir_input import bundle_to_input, input_to_bundle
from cdss.domain.decision_tree import InvalidFhirInput

_BP_ROLES = [
    ("current_clinic", "current_clinic_sbp", "current_clinic_dbp"),
    ("previous_visit", "previous_sbp", "previous_dbp"),
    ("clinic_1", "clinic_1_sbp", "clinic_1_dbp"),
]


def test_patient_birthdate_maps_to_age() -> None:
    this_year = datetime.now(UTC).date().year
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": {"resourceType": "Patient", "birthDate": f"{this_year - 52}-01-01"}}],
    }

    assert bundle_to_input(bundle)["age"] == 52


@pytest.mark.parametrize(("role", "sbp_key", "dbp_key"), _BP_ROLES)
def test_bp_reading_role_round_trips(role: str, sbp_key: str, dbp_key: str) -> None:
    flat = {sbp_key: 150, dbp_key: 95}

    bundle = input_to_bundle(flat)
    observation = bundle["entry"][0]["resource"]
    assert observation["resourceType"] == "Observation"
    assert {ext["valueCode"] for ext in observation["extension"]} == {role}

    assert bundle_to_input(bundle) == flat


def test_bp_observation_missing_reading_role_extension_is_rejected() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
                    "component": [
                        {
                            "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                            "valueQuantity": {"value": 140, "unit": "mmHg"},
                        }
                    ],
                }
            }
        ],
    }

    with pytest.raises(InvalidFhirInput):
        bundle_to_input(bundle)


@pytest.mark.parametrize(
    ("key", "value"),
    [("acr_mg_mmol", 3.5), ("proteinuria_24h_mg", 250)],
)
def test_lab_observation_round_trips(key: str, value: float) -> None:
    flat = {key: value}
    assert bundle_to_input(input_to_bundle(flat)) == flat


def test_true_clinical_flag_round_trips_as_confirmed_condition() -> None:
    flat = {"has_diabetes": True, "is_pregnant": True}

    bundle = input_to_bundle(flat)
    for entry in bundle["entry"]:
        resource = entry["resource"]
        assert resource["resourceType"] == "Condition"
        assert resource["verificationStatus"]["coding"][0]["code"] == "confirmed"

    assert bundle_to_input(bundle) == flat


def test_false_clinical_flag_round_trips_as_refuted_condition() -> None:
    flat = {"has_diabetes": False}

    bundle = input_to_bundle(flat)
    resource = bundle["entry"][0]["resource"]
    assert resource["resourceType"] == "Condition"
    assert resource["verificationStatus"]["coding"][0]["code"] == "refuted"

    assert bundle_to_input(bundle) == flat


def test_condition_with_no_verification_status_defaults_to_true() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "code": {
                        "coding": [
                            {
                                "system": "http://cdss.local/fhir/CodeSystem/clinical-flag",
                                "code": "has_heart_failure",
                            }
                        ]
                    },
                }
            }
        ],
    }

    assert bundle_to_input(bundle) == {"has_heart_failure": True}


def test_workflow_flag_is_routed_to_parameters_not_condition() -> None:
    flat = {"is_medication_follow_up": True, "has_prior_prescription": False}

    bundle = input_to_bundle(flat)
    resource = bundle["entry"][0]["resource"]
    assert resource["resourceType"] == "Parameters"
    names = {p["name"] for p in resource["parameter"]}
    assert names == {"is_medication_follow_up", "has_prior_prescription"}

    assert bundle_to_input(bundle) == flat


def test_nested_object_round_trips_via_parameters_part() -> None:
    flat = {
        "active_bp_target": {
            "sbp": {"upper_exclusive_mmhg": 130},
            "dbp": {"upper_exclusive_mmhg": 80},
            "source": "CALLER_SUPPLIED",
        }
    }

    assert bundle_to_input(input_to_bundle(flat)) == flat


def test_array_round_trips_via_parameters_part_with_array_extension() -> None:
    flat = {"contraindicated_drug_classes": ["MRA", "ALPHA_BLOCKER"]}

    assert bundle_to_input(input_to_bundle(flat)) == flat


def test_single_element_array_is_not_confused_with_a_scalar() -> None:
    flat = {"contraindicated_drug_classes": ["MRA"]}

    bundle = input_to_bundle(flat)
    result = bundle_to_input(bundle)
    assert result["contraindicated_drug_classes"] == ["MRA"]
    assert isinstance(result["contraindicated_drug_classes"], list)


def test_empty_array_round_trips_distinctly_from_empty_object() -> None:
    flat = {"empty_list": [], "empty_object": {}}

    assert bundle_to_input(input_to_bundle(flat)) == flat


def test_opaque_unknown_key_passes_through_unchanged() -> None:
    flat = {"request_id": "abc-123", "patient_external_id": "must-not-be-stored"}

    assert bundle_to_input(input_to_bundle(flat)) == flat


def test_full_representative_round_trip() -> None:
    flat = {
        "age": 55,
        "is_pregnant": False,
        "has_diabetes": True,
        "has_heart_failure": False,
        "current_clinic_sbp": 150,
        "current_clinic_dbp": 95,
        "previous_sbp": 160,
        "previous_dbp": 100,
        "acr_mg_mmol": 4.2,
        "facility_capability": "FULL_RESOURCES",
        "is_medication_follow_up": True,
        "medication_follow_up_stage": "INITIAL_REGIMEN",
        "active_bp_target": {
            "sbp": {"upper_exclusive_mmhg": 130},
            "dbp": {"upper_exclusive_mmhg": 80},
            "source": "CALLER_SUPPLIED",
        },
        "contraindicated_drug_classes": ["MRA", "ALPHA_BLOCKER"],
        "risk_factor_count": 3,
    }

    assert bundle_to_input(input_to_bundle(flat)) == flat


def test_non_bundle_root_is_rejected() -> None:
    with pytest.raises(InvalidFhirInput):
        bundle_to_input({"resourceType": "Patient"})

    with pytest.raises(InvalidFhirInput):
        bundle_to_input({"foo": "bar"})

    with pytest.raises(InvalidFhirInput):
        bundle_to_input([])


def test_bundle_entry_missing_resource_is_rejected() -> None:
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [{}]}

    with pytest.raises(InvalidFhirInput):
        bundle_to_input(bundle)


def test_parameters_entry_missing_name_is_rejected() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": [{"valueString": "no name here"}],
                }
            }
        ],
    }

    with pytest.raises(InvalidFhirInput):
        bundle_to_input(bundle)


def test_unrecognized_resource_type_is_ignored() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": {"resourceType": "Encounter", "status": "finished"}}],
    }

    assert bundle_to_input(bundle) == {}
