"""FHIR R4 and traversal contracts for every pregnancy simulator preset."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft6Validator
from referencing import Registry, Resource
from sqlalchemy.orm import Session

from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.domain.decision_tree import NodeType, TraceEvent, walk_tree
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository

pytestmark = pytest.mark.database

ROOT = Path(__file__).parents[2]
PRESET_DIR = ROOT / "data" / "fhir" / "pregnancy_presets"
SCHEMA_PATH = ROOT / "tests" / "fhir" / "schema" / "fhir.schema.json"
PRESET_FILES = tuple(sorted(PRESET_DIR.glob("*.json")))
META_BASE = "http://cdss.local/fhir/CodeSystem/preset"


@pytest.fixture(scope="module")
def fhir_bundle_validator() -> Draft6Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    base_uri = schema["id"]
    registry = Registry().with_resource(base_uri, Resource.from_contents(schema))
    return Draft6Validator(
        {"$ref": f"{base_uri}#/definitions/Bundle"},
        registry=registry,
    )


@pytest.mark.parametrize("preset_path", PRESET_FILES, ids=lambda path: path.stem)
def test_pregnancy_preset_is_strict_fhir_r4(
    preset_path: Path,
    fhir_bundle_validator: Draft6Validator,
) -> None:
    bundle = _load(preset_path)
    errors = sorted(
        fhir_bundle_validator.iter_errors(bundle),
        key=lambda error: list(error.path),
    )
    assert not errors, "\n".join(f"{list(error.path)}: {error.message}" for error in errors)

    entries = bundle["entry"]
    resources = [entry["resource"] for entry in entries]
    assert len([resource for resource in resources if resource["resourceType"] == "Patient"]) == 1
    assert all(
        entry["fullUrl"]
        == (
            f"http://example.org/fhir/{entry['resource']['resourceType']}/{entry['resource']['id']}"
        )
        for entry in entries
    )


@pytest.mark.parametrize("preset_path", PRESET_FILES, ids=lambda path: path.stem)
def test_pregnancy_preset_reaches_expected_nodes_in_auto_and_manual_modes(
    seeded_session: Session,
    preset_path: Path,
) -> None:
    bundle = _load(preset_path)
    parsed = parse_clinical_bundle(bundle)
    repository = SqlAlchemyTreeGraphRepository(seeded_session)
    expected_nodes = set(_meta_codes(bundle, "expected-node"))
    expected_terminal = _single_meta_code(bundle, "expected-terminal")

    auto_result = walk_tree(
        repository.get_tree("hypertension-diagnosis"),
        deepcopy(parsed.runtime_input),
        repository=repository,
    )
    manual_result = walk_tree(
        repository.get_tree("hypertension-in-pregnancy"),
        deepcopy(parsed.runtime_input),
        repository=repository,
    )

    for mode, result in (("auto", auto_result), ("manual", manual_result)):
        entered = {
            entry.node_key
            for entry in result.trace
            if entry.event is TraceEvent.NODE_ENTERED
            and entry.tree_key == "hypertension-in-pregnancy"
        }
        assert expected_nodes <= entered, (
            f"{mode} traversal missed {sorted(expected_nodes - entered)}; entered {sorted(entered)}"
        )
        assert expected_terminal in entered, (
            f"{mode} traversal did not reach {expected_terminal}; entered {sorted(entered)}"
        )


def test_pregnancy_catalog_covers_every_tree_12_terminal() -> None:
    terminals = {_single_meta_code(_load(path), "expected-terminal") for path in PRESET_FILES}
    assert terminals == {
        "T12_END_FOLLOW_UP_MONITOR",
        "T12_END_PRE_EXISTING_HTN",
        "T12_END_ASPIRIN_PROPHYLAXIS",
        "T12_END_MAINTAIN_REGIMEN_PREGNANT",
        "T12_END_REFER_OBGYN",
        "T12_END_EMERGENCY_DELIVERY",
        "T12_END_MAINTAIN_REGIMEN_POSTPARTUM",
    }


def test_pregnancy_catalog_executes_every_reachable_tree_12_node(
    seeded_session: Session,
) -> None:
    repository = SqlAlchemyTreeGraphRepository(seeded_session)
    graph = repository.get_tree("hypertension-in-pregnancy")
    entered: set[str] = set()
    for path in PRESET_FILES:
        runtime_input = parse_clinical_bundle(_load(path)).runtime_input
        result = walk_tree(graph, runtime_input, repository=repository)
        entered.update(
            entry.node_key
            for entry in result.trace
            if entry.event is TraceEvent.NODE_ENTERED
            and entry.tree_key == "hypertension-in-pregnancy"
        )

    executable = {
        node.node_key
        for node in graph.nodes_by_id.values()
        if node.node_type is not NodeType.GLOBAL
    }
    assert executable <= entered, f"Uncovered Tree 12 nodes: {sorted(executable - entered)}"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _meta_codes(bundle: dict[str, Any], suffix: str) -> list[str]:
    system = f"{META_BASE}/{suffix}"
    return [str(tag["code"]) for tag in bundle["meta"]["tag"] if tag.get("system") == system]


def _single_meta_code(bundle: dict[str, Any], suffix: str) -> str:
    values = _meta_codes(bundle, suffix)
    assert len(values) == 1
    return values[0]
