from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.api.schemas.clinical_presentation import build_presentation
from cdss.domain.decision_tree import (
    ExecutedAction,
    ExecutedReference,
    InvalidFhirInput,
    NodeType,
    TraceEvent,
    TraversalTraceEntry,
)

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


def test_alert_summary_contains_only_physician_readable_traversed_findings() -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    runtime_input = dict(parsed.runtime_input)
    runtime_input["has_target_organ_damage"] = True
    runtime_input["has_stroke"] = True
    parsed = replace(parsed, runtime_input=runtime_input)
    action = ExecutedAction(
        tree_key="hypertensive-emergency",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Recommendation",
        text_vi="Khuyến nghị",
        payload={},
    )
    trace = [
        TraversalTraceEntry(
            step=1,
            event=TraceEvent.CANDIDATE_EVALUATED,
            tree_key="hypertensive-emergency",
            node_key="T14_START",
            node_type=NodeType.START,
            candidate_node_key="T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE",
            condition_definition={
                "op": "eq",
                "path": "input.has_target_organ_damage",
                "value": True,
            },
            condition_result=True,
        )
    ]

    summary = build_presentation(action, parsed, [], trace=trace)["alert_summary"]

    assert summary["text_en"] == "Patient has clinical findings requiring review."
    assert summary["text_vi"] == "Bệnh nhân có các phát hiện lâm sàng cần được đánh giá."
    assert summary["findings"] == [
        {
            "code": "has_target_organ_damage",
            "label_en": "Target-organ damage",
            "label_vi": "Tổn thương cơ quan đích",
            "tree_key": "hypertensive-emergency",
            "node_key": "T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE",
        }
    ]
    assert "_" not in summary["text_en"]
    assert "Stroke" not in summary["text_en"]


def test_alert_summary_includes_risk_classified_by_the_traversed_risk_tree() -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    action = ExecutedAction(
        tree_key="treatment",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Recommendation",
        text_vi="Khuyến nghị",
        payload={},
    )
    trace = [
        TraversalTraceEntry(
            step=1,
            event=TraceEvent.NODE_ENTERED,
            tree_key="risk-classification",
            node_key="T2_INF_GRADE_2_HIGH_RISK",
            node_type=NodeType.INFERENCE,
            changed_context_paths=["context.risk.level"],
        )
    ]

    summary = build_presentation(
        action,
        parsed,
        [],
        trace=trace,
        context={"risk": {"level": "HIGH"}},
    )["alert_summary"]

    assert summary["text_en"] == "Patient has High Hypertension Risk"
    assert summary["text_vi"] == "Bệnh nhân có Nguy cơ tăng huyết áp cao"
    assert summary["risk_level"] == {
        "code": "HIGH",
        "label_en": "High Hypertension Risk",
        "label_vi": "Nguy cơ tăng huyết áp cao",
    }


@pytest.mark.parametrize(
    ("node_key", "expected_code", "expected_en", "expected_vi"),
    [
        (
            "T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE",
            "EMERGENCY_HYPERTENSION",
            "Emergency Hypertension",
            "Tăng huyết áp cấp cứu",
        ),
        (
            "T14_C_NO_ACUTE_TARGET_ORGAN_DAMAGE",
            "URGENCY_HTN",
            "Urgency Hypertension",
            "Tăng huyết áp khẩn trương",
        ),
    ],
)
def test_alert_summary_identifies_the_traversed_hypertensive_crisis_branch(
    node_key: str,
    expected_code: str,
    expected_en: str,
    expected_vi: str,
) -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    action = ExecutedAction(
        tree_key="hypertensive-emergency",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Recommendation",
        text_vi="Khuyến nghị",
        payload={},
    )
    trace = [
        TraversalTraceEntry(
            step=1,
            event=TraceEvent.NODE_ENTERED,
            tree_key="hypertensive-emergency",
            node_key=node_key,
            node_type=NodeType.CONDITION,
        )
    ]

    summary = build_presentation(action, parsed, [], trace=trace)["alert_summary"]

    assert summary["text_en"] == f"Patient has {expected_en}"
    assert summary["text_vi"] == f"Bệnh nhân có {expected_vi}"
    assert summary["hypertensive_crisis_classification"]["code"] == expected_code


def test_alert_summary_does_not_show_untraversed_context_risk() -> None:
    bundle = json.loads(next(iter(sorted(FIXTURE_DIR.glob("*.json")))).read_text(encoding="utf-8"))
    parsed = parse_clinical_bundle(bundle)
    action = ExecutedAction(
        tree_key="treatment",
        node_key="terminal",
        node_type=NodeType.END,
        text_en="Recommendation",
        text_vi="Khuyến nghị",
        payload={},
    )

    summary = build_presentation(
        action,
        parsed,
        [],
        context={"risk": {"level": "HIGH"}},
    )["alert_summary"]

    assert "cardiovascular risk" not in summary["text_en"]
    assert "risk_level" not in summary


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
    trace = [
        TraversalTraceEntry(
            step=1,
            event=TraceEvent.NODE_ENTERED,
            tree_key="drug-combination",
            node_key="T6_INF_INITIATE_TWO_DRUG_LOW_DOSE",
            node_type=NodeType.INFERENCE,
            changed_context_paths=[
                "context.treatment_preferences.dose_strategy",
                "context.treatment_preferences.combination_options",
            ],
        )
    ]
    references = [
        ExecutedReference(
            tree_key="drug-combination",
            tree_name_en="Drug combination",
            tree_name_vi="Phối hợp thuốc",
            node_key="T6_INF_INITIATE_TWO_DRUG_LOW_DOSE",
            node_text_en="Drug therapy: start with 2 low-dose drugs (A combined with C or D)",
            node_text_vi="Điều trị thuốc khởi đầu bằng 2 thuốc liều thấp",
            reference_order=1,
            source_title="VSH/VNHA Hypertension Guideline 2022",
            section_path=[{"number": "3.5", "title": "Combination treatment strategy"}],
            locator="Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc",
            locator_detail="Prefer A+C or A+D at low dose.",
            printed_page_numbers=[20],
            pdf_page_numbers=[22],
            reference_note="Use a low-dose fixed combination.",
        )
    ]

    order = build_presentation(action, parsed, references, trace=trace)["recommended_orders"][0]

    assert order["name_en"] == "Drug Class A + Drug Class C"
    assert order["dose_strategy"] == "LOW_DOSE"
    assert order["drug_classes"][0]["medicines"] == [
        {"id": "losartan", "name": "Losartan", "dose": "25 mg", "route": "", "subgroup": ""}
    ]
    assert order["drug_classes"][1]["medicines"][0]["dose"] == "2.5 mg"
    assert order["strategy_references"][0]["locator"] == (
        "Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc"
    )
    assert order["strategy_references"][0]["node_text_en"].startswith(
        "Drug therapy: start with 2 low-dose drugs"
    )


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
