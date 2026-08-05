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
    assert parsed.runtime_input["current_clinic_sbp"] > 0
    assert parsed.runtime_input["current_clinic_dbp"] > 0
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
    assert parsed.runtime_input["active_medication_regimen"]
    assert any(item["category"] == "medication" for item in parsed.clinical_details)


def test_medication_statement_is_added_to_active_regimen() -> None:
    bundle = json.loads(
        (FIXTURE_DIR / "PT0001.json").read_text(encoding="utf-8")
    )
    bundle["entry"].append(
        {
            "resource": {
                "resourceType": "MedicationStatement",
                "id": "statement-1",
                "status": "active",
                "medicationCodeableConcept": {"text": "Enalapril"},
                "subject": {"reference": "Patient/PT0001"},
                "effectiveDateTime": "2026-08-04",
            }
        }
    )

    parsed = parse_clinical_bundle(bundle)

    statement = next(
        item
        for item in parsed.runtime_input["active_medication_regimen"]
        if item["source_reference"] == "MedicationStatement/statement-1"
    )
    assert statement["name"] == "Enalapril"
    assert statement["effective_time"] == "2026-08-04"


def test_low_dose_combination_presents_class_medicines_with_only_low_doses() -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    action = ExecutedAction(
        tree_key="drug-combination",
        node_key="T6_END_INITIAL_TWO_DRUG_COMBINATION",
        node_type=NodeType.END,
        text_en="Start two-drug low-dose combination",
        text_vi="Khởi trị phối hợp hai thuốc liều thấp",
        payload={
            "medicine_options": [
                {
                    "classes": ["A", "C"],
                    "dose_strategy": "LOW_DOSE",
                    "medicines": {
                        "A": [
                            {
                                "drug_id": "losartan",
                                "name": "Losartan",
                                "dose_low": "25 mg",
                                "dose_usual": "50 - 100 mg",
                                "available": True,
                            }
                        ],
                        "C": [
                            {
                                "drug_id": "amlodipine",
                                "name": "Amlodipine",
                                "dose_low": "2.5 mg",
                                "dose_usual": "5 - 10 mg",
                                "available": True,
                            }
                        ],
                    },
                }
            ]
        },
    )

    order = build_presentation(action, parsed, [])["recommended_orders"][0]

    assert order["name_en"] == "Drug Class A + Drug Class C"
    assert order["dose_strategy"] == "LOW_DOSE"
    assert order["drug_classes"][0]["medicines"] == [
        {"id": "losartan", "name": "Losartan", "dose": "25 mg", "route": "", "subgroup": ""}
    ]
    assert order["drug_classes"][1]["medicines"][0]["dose"] == "2.5 mg"


def test_single_medicine_presents_its_complete_catalog_class() -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    class_a = [
        {
            "drug_id": "enalapril",
            "name": "Enalapril",
            "drug_class": "A",
            "subgroup": "ƯCMC",
            "route": "Thuốc Uống",
            "dose_low": "5 mg",
            "dose_usual": "10–20 mg",
            "available": True,
        },
        {
            "drug_id": "losartan",
            "name": "Losartan",
            "drug_class": "A",
            "subgroup": "CTTA",
            "route": "Thuốc Uống",
            "dose_low": "25 mg",
            "dose_usual": "50–100 mg",
            "available": True,
        },
    ]
    action = ExecutedAction(
        tree_key="example",
        node_key="single-enalapril",
        node_type=NodeType.END,
        text_en="Start Enalapril",
        text_vi="Start Enalapril",
        payload={
            "medicines": [class_a[0]],
            "medicine_catalog_by_class": {"A": class_a},
        },
    )

    order = build_presentation(action, parsed, [])["recommended_orders"][0]

    assert order["name_en"] == "Enalapril"
    assert order["class_label_en"] == "A"
    assert [medicine["name"] for medicine in order["drug_classes"][0]["medicines"]] == [
        "Enalapril",
        "Losartan",
    ]


def test_combination_hover_uses_complete_database_catalog() -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    oral = {
        "drug_id": "amlodipine",
        "name": "Amlodipine",
        "drug_class": "C",
        "route": "Thuốc Uống",
        "available": True,
    }
    intravenous = {
        "drug_id": "nicardipine",
        "name": "Nicardipine",
        "drug_class": "C",
        "route": "Thuốc Truyền Tĩnh Mạch",
        "available": True,
    }
    action = ExecutedAction(
        tree_key="example",
        node_key="class-c",
        node_type=NodeType.END,
        text_en="Start a calcium-channel blocker",
        text_vi="Start a calcium-channel blocker",
        payload={
            "medicine_options": [{"classes": ["C"], "medicines": {"C": [oral]}}],
            "medicine_catalog_by_class": {"C": [oral, intravenous]},
        },
    )

    order = build_presentation(action, parsed, [])["recommended_orders"][0]

    assert [item["name"] for item in order["drug_classes"][0]["medicines"]] == [
        "Amlodipine",
        "Nicardipine",
    ]


def test_explicit_orders_keep_additional_traversed_drugs_without_duplicates() -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    aspirin = {
        "drug_id": "aspirin",
        "name": "Aspirin",
        "drug_class": "ANTIPLATELET",
        "dose_low": "81 mg",
        "available": True,
    }
    spironolactone = {
        "drug_id": "spironolactone",
        "name": "Spironolactone",
        "drug_class": "MRA",
        "dose_low": "12.5 mg",
        "available": True,
    }
    action = ExecutedAction(
        tree_key="example",
        node_key="multi-step-regimen",
        node_type=NodeType.END,
        text_en="Use the traversed regimen",
        text_vi="Use the traversed regimen",
        payload={
            "recommended_orders": [
                {
                    "id": "explicit-aspirin",
                    "type": "medication",
                    "name_en": "Aspirin",
                    "name_vi": "Aspirin",
                    "dose": "81 mg",
                    "medicine_ids": ["aspirin"],
                }
            ],
            "medicines": [aspirin, spironolactone],
        },
    )

    orders = build_presentation(action, parsed, [])["recommended_orders"]

    assert [(order["name_en"], order.get("dose")) for order in orders] == [
        ("Aspirin", "81 mg"),
        ("Spironolactone", "12.5 mg"),
    ]


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


@pytest.mark.parametrize(
    ("flag", "active"),
    [
        ("drug_replacement_required", True),
        ("adherence_adequate", False),
        ("dose_adequate", True),
    ],
)
def test_medication_follow_up_flags_survive_canonical_parsing(flag: str, active: bool) -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    patient_id = bundle["entry"][0]["resource"]["id"]
    bundle["entry"].append(
        {
            "resource": {
                "resourceType": "Condition",
                "id": f"{patient_id}-{flag}",
                "subject": {"reference": f"Patient/{patient_id}"},
                "code": {
                    "coding": [
                        {
                            "system": "http://cdss.local/fhir/CodeSystem/clinical-flag",
                            "code": flag,
                        }
                    ]
                },
                "verificationStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                            "code": "confirmed" if active else "refuted",
                        }
                    ]
                },
            }
        }
    )

    parsed = parse_clinical_bundle(bundle)

    assert parsed.runtime_input[flag] is active


def test_omitted_adherence_and_dose_flags_remain_unspecified() -> None:
    parsed = parse_clinical_bundle(
        json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    )

    assert "adherence_adequate" not in parsed.runtime_input
    assert "dose_adequate" not in parsed.runtime_input
