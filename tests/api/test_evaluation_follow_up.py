"""Canonical visit-history routing contract tests."""

from __future__ import annotations

import pytest

from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.domain.decision_tree import InvalidFhirInput
from cdss.main import create_app


def test_separate_follow_up_endpoint_is_retired() -> None:
    assert "/evaluate/follow-up" not in {
        path
        for route in create_app().routes
        if isinstance(path := getattr(route, "path", None), str)
    }


def test_two_encounters_map_immediately_previous_and_current_readings() -> None:
    parsed = parse_clinical_bundle(_longitudinal_bundle())

    assert parsed.runtime_input["previous_sbp"] == 150
    assert parsed.runtime_input["previous_dbp"] == 95
    assert parsed.runtime_input["current_clinic_sbp"] == 128
    assert parsed.runtime_input["current_clinic_dbp"] == 78
    assert parsed.runtime_input["facility_capability"] == "LIMITED_RESOURCES"
    assert {item["category"] for item in parsed.clinical_details} >= {
        "previous_reading",
        "historical_encounter",
    }
    assert parsed.patient_id == "follow-up-patient"
    assert parsed.encounter_ids == ("previous", "current")


def test_longitudinal_bundle_requires_complete_latest_bp_pair() -> None:
    bundle = _longitudinal_bundle()
    bundle["entry"] = [
        entry for entry in bundle["entry"] if entry["resource"].get("id") != "current-dbp"
    ]

    with pytest.raises(InvalidFhirInput) as exc_info:
        parse_clinical_bundle(bundle)

    assert "current_clinic blood pressure" in exc_info.value.details["reason"]


def test_declared_pregnancy_follow_up_number_must_match_prior_encounters() -> None:
    bundle = _longitudinal_bundle()
    patient = bundle["entry"][0]["resource"]
    patient["extension"] = [
        {
            "url": ("http://cdss.local/fhir/StructureDefinition/input/pregnancy_follow_up_number"),
            "valueInteger": 3,
        }
    ]

    with pytest.raises(InvalidFhirInput) as exc_info:
        parse_clinical_bundle(bundle)

    assert "pregnancy_follow_up_number" in exc_info.value.details["reason"]


def _longitudinal_bundle() -> dict:
    patient_id = "follow-up-patient"
    entries = [
        {"resource": {"resourceType": "Patient", "id": patient_id, "birthDate": "1970-01-01"}},
        {"resource": _encounter(patient_id, "previous", "2026-01-01", [])},
        {
            "resource": _encounter(
                patient_id,
                "current",
                "2026-02-01",
                [
                    {
                        "url": "http://cdss.local/fhir/StructureDefinition/facility-capability",
                        "valueString": "LIMITED_RESOURCES",
                    }
                ],
            )
        },
        {"resource": _bp(patient_id, "previous", "previous-sbp", "8459-0", 150)},
        {"resource": _bp(patient_id, "previous", "previous-dbp", "8462-4", 95)},
        {"resource": _bp(patient_id, "current", "current-sbp", "8459-0", 128)},
        {"resource": _bp(patient_id, "current", "current-dbp", "8462-4", 78)},
    ]
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def _encounter(patient_id: str, encounter_id: str, start: str, extensions: list[dict]) -> dict:
    return {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {"start": start},
        "extension": extensions,
    }


def _bp(patient_id: str, encounter_id: str, observation_id: str, code: str, value: int) -> dict:
    return {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": code}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "valueQuantity": {"value": value, "unit": "mmHg"},
    }
