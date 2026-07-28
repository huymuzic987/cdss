from __future__ import annotations

import json
from pathlib import Path

import pytest

from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.api.schemas.clinical_presentation import build_presentation
from cdss.domain.decision_tree import ExecutedAction, InvalidFhirInput, NodeType

FIXTURE_DIR = Path(__file__).parents[2] / "data" / "fhir" / "test_case"


@pytest.mark.parametrize("path", sorted(FIXTURE_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_reference_bundle_has_canonical_runtime_and_presentation(path: Path) -> None:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)

    assert parsed.raw_bundle == bundle
    assert parsed.runtime_input["clinic_1_sbp"] > 0
    assert parsed.runtime_input["clinic_1_dbp"] > 0
    assert parsed.runtime_input["facility_capability"] == "FULL_RESOURCES"
    assert parsed.runtime_input["is_pregnant"] is False
    assert {item["id"] for item in parsed.trigger_evidence} == {
        "current-sbp",
        "current-dbp",
    }

    action = ExecutedAction(
        tree_key="hypertension-diagnosis",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Recommendation",
        text_vi="Khuyến nghị",
        payload={},
    )
    presentation = build_presentation(action, parsed, [])
    assert presentation["schema_version"] == "1.0"
    assert presentation["alert"]["text_en"]
    assert presentation["recommendation"] == {
        "text_en": "Recommendation",
        "text_vi": "Khuyến nghị",
    }
    assert len(presentation["trigger_evidence"]) == 2
    categories = {item["category"] for item in presentation["clinical_details"]}
    assert "laboratory" in categories


def test_medications_are_presentation_details_even_when_not_runtime_inputs() -> None:
    path = next(
        path
        for path in sorted(FIXTURE_DIR.glob("*.json"))
        if "MedicationRequest" in path.read_text(encoding="utf-8")
    )
    parsed = parse_clinical_bundle(json.loads(path.read_text(encoding="utf-8")))

    assert "medications" not in parsed.runtime_input
    assert any(item["category"] == "medication" for item in parsed.clinical_details)


def test_legacy_parameters_resource_is_rejected() -> None:
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p1"}},
            {"resource": {"resourceType": "Parameters", "parameter": []}},
        ],
    }

    with pytest.raises(InvalidFhirInput) as exc_info:
        parse_clinical_bundle(bundle)

    assert "canonical clinical profile" in exc_info.value.details["reason"]
