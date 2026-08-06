"""Validate generated patient presets and their lookup-table SNOMED provenance."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft6Validator
from referencing import Registry, Resource

ROOT = Path(__file__).parents[2]
PRESET_ROOT = ROOT / "data" / "fhir"
SEED_PATH = ROOT / "backups" / "seed.sql"
SCHEMA_PATH = ROOT / "tests" / "fhir" / "schema" / "fhir.schema.json"
SNOMED_SYSTEM = "http://snomed.info/sct"
REFERENCE_TABLES = ("medicines", "symptoms", "contraindication_drugs")
SNOMED_COLUMNS = ("snomed_code", "snomedct_2026_06_01")


def test_generated_patient_presets_are_strict_fhir_and_use_reference_snomed_codes() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    base_uri = schema["id"]
    registry = Registry().with_resource(base_uri, Resource.from_contents(schema))
    validator = Draft6Validator(
        {"$ref": f"{base_uri}#/definitions/Bundle"},
        registry=registry,
    )
    reference_codes = _reference_snomed_codes()
    preset_files = sorted(PRESET_ROOT.glob("*_presets/*.json"))

    assert len(preset_files) == 114
    assert reference_codes

    seen_codes: set[str] = set()
    for preset_path in preset_files:
        bundle = json.loads(preset_path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(bundle), key=lambda error: list(error.path))
        assert not errors, f"{preset_path}: " + "; ".join(
            f"{list(error.path)}: {error.message}" for error in errors
        )

        entries = bundle["entry"]
        resources = [entry["resource"] for entry in entries]
        assert sum(resource["resourceType"] == "Patient" for resource in resources) == 1
        for entry in entries:
            resource = entry["resource"]
            assert entry["fullUrl"] == (
                f"http://example.org/fhir/{resource['resourceType']}/{resource['id']}"
            )
            for coding in _codings(resource):
                if coding.get("system") != SNOMED_SYSTEM:
                    continue
                code = coding.get("code")
                assert code in reference_codes, f"{preset_path}: unknown SNOMED CT code {code}"
                seen_codes.add(code)

    assert seen_codes


def _codings(resource: dict[str, Any]) -> list[dict[str, Any]]:
    if resource.get("resourceType") == "Condition":
        code = resource.get("code")
    elif resource.get("resourceType") == "MedicationRequest":
        code = resource.get("medicationCodeableConcept")
    else:
        return []
    return [item for item in code.get("coding", []) if isinstance(item, dict)] if isinstance(code, dict) else []


def _reference_snomed_codes() -> set[str]:
    sql = SEED_PATH.read_text(encoding="utf-8")
    codes: set[str] = set()
    for table in REFERENCE_TABLES:
        pattern = re.compile(
            rf"INSERT INTO public\.{table}\s*\((?P<columns>[^)]*)\)\s*"
            rf"VALUES\s*\((?P<values>[\s\S]*?)\)\s*ON CONFLICT",
            re.IGNORECASE,
        )
        for match in pattern.finditer(sql):
            columns = [column.strip() for column in match.group("columns").split(",")]
            values = _split_sql_values(match.group("values"))
            for column, value in zip(columns, values):
                if column in SNOMED_COLUMNS and value.upper() != "NULL":
                    code = value[1:-1].replace("''", "'") if value.startswith("'") else value
                    if code:
                        codes.add(code)
    return codes


def _split_sql_values(value: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    quoted = False
    index = 0
    while index < len(value):
        char = value[index]
        if char == "'":
            current.append(char)
            if quoted and index + 1 < len(value) and value[index + 1] == "'":
                current.append(value[index + 1])
                index += 1
            else:
                quoted = not quoted
        elif char == "," and not quoted:
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    fields.append("".join(current).strip())
    return fields
