from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.domain.contraindication_catalog import ContraindicationDrug
from cdss.domain.contraindication_evaluator import prepare_contraindication_input
from cdss.domain.medication_safety import evaluate_target

PRESET_PATH = Path(__file__).parents[2] / "data" / "fhir" / "preset_patients.json"


def _rule(**changes: object) -> ContraindicationDrug:
    values = {
        "contraindication_id": "CDTEST",
        "disease_finding_vn": "Hen",
        "disease_finding_eng": "Asthma",
        "contraindication_type": "absolute",
        "drug_group": "Chẹn beta",
        "drugs": None,
        "icd10_vn_1_decimal": "J45.9",
        "snomedct_2026_06_01": "195967001",
        "target": "BETA_BLOCKER",
        "finding_key": "ASTHMA",
        "fact_key": "asthma_severity",
    }
    values.update(changes)
    return ContraindicationDrug(**values)


def _preset_0001_bundle() -> dict[str, Any]:
    source = json.loads(PRESET_PATH.read_text(encoding="utf-8"))
    patient_id = "preset-0001"
    entries = []
    for entry in source["entry"]:
        resource = entry["resource"]
        reference = (resource.get("subject") or {}).get("reference")
        if resource.get("id") == patient_id or reference == f"Patient/{patient_id}":
            entries.append(entry)
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def test_preset_0001_is_read_as_fhir_and_has_no_catalog_contraindication() -> None:
    bundle = _preset_0001_bundle()
    parsed = parse_clinical_bundle(bundle)

    prepare_contraindication_input(parsed.runtime_input, bundle, [_rule()])

    assert parsed.patient_id == "preset-0001"
    assert parsed.runtime_input["eGFR"] > 30
    assert parsed.runtime_input["serum_potassium"] < 5.5
    assert parsed.runtime_input["contraindication_findings"] == []
    assert parsed.runtime_input["contraindicated_drug_classes"] == []


def test_condition_code_is_matched_before_tree_traversal_and_blocks_target() -> None:
    bundle = _preset_0001_bundle()
    bundle["entry"].append(
        {
            "resource": {
                "resourceType": "Condition",
                "id": "preset-0001-cond-asthma",
                "subject": {"reference": "Patient/preset-0001"},
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": "J45.9",
                        }
                    ]
                },
            }
        }
    )
    parsed = parse_clinical_bundle(bundle)

    prepare_contraindication_input(parsed.runtime_input, bundle, [_rule()])
    beta = evaluate_target("BETA_BLOCKER", parsed.runtime_input)

    assert parsed.runtime_input["contraindicated_drug_classes"] == ["BETA_BLOCKER"]
    assert beta["status"] == "ABSOLUTE"
    assert beta["findings"][0]["reason_code"] == "ASTHMA"
    assert beta["findings"][0]["evidence"][0]["source"] == (
        "Condition/preset-0001-cond-asthma"
    )


def test_same_finding_keeps_each_contraindicated_drug_subgroup() -> None:
    bundle = _preset_0001_bundle()
    bundle["entry"].append(
        {
            "resource": {
                "resourceType": "Condition",
                "id": "preset-0001-cond-gout",
                "subject": {"reference": "Patient/preset-0001"},
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": "M10.9",
                        }
                    ]
                },
            }
        }
    )
    parsed = parse_clinical_bundle(bundle)
    rules = [
        _rule(
            contraindication_id="CD-GOUT-THIAZIDE",
            disease_finding_eng="Gout",
            drug_group="LT Thiazide",
            icd10_vn_1_decimal="M10.9",
            snomedct_2026_06_01=None,
            target="THIAZIDE_LIKE_DIURETIC",
            finding_key="GOUT",
        ),
        _rule(
            contraindication_id="CD-GOUT-THIAZIDE-LIKE",
            disease_finding_eng="Gout",
            drug_group="LT Thiazide-like",
            icd10_vn_1_decimal="M10.9",
            snomedct_2026_06_01=None,
            target="THIAZIDE_LIKE_DIURETIC",
            finding_key="GOUT",
        ),
    ]

    prepare_contraindication_input(parsed.runtime_input, bundle, rules)

    assert [
        item["drug_group"] for item in parsed.runtime_input["contraindication_findings"]
    ] == ["LT Thiazide", "LT Thiazide-like"]
