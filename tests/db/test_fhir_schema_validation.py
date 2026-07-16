"""Validate real seeded-tree-derived FHIR resources against the official HL7 FHIR R4 schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft6Validator
from referencing import Registry, Resource
from sqlalchemy import select
from sqlalchemy.orm import Session

from cdss.api.schemas.fhir import Bundle, Library, PlanDefinition
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository
from cdss.infrastructure.db.models import DecisionTree

pytestmark = pytest.mark.database

SEEDED_TREE_KEYS = [
    "hypertension-diagnosis",
    "risk-classification",
    "treatment-threshold-and-bp-target",
    "essential-treatment-strategy",
    "optimal-treatment-strategy",
    "drug-combination",
    "hypertension-type-2-diabetes",
    "hypertension-coronary-artery-disease",
    "hypertension-heart-failure",
    "hypertension-chronic-kidney-disease",
    "hypertension-in-pregnancy",
    "resistant-hypertension",
    "hypertensive-emergency",
]

_SCHEMA_PATH = Path(__file__).parent.parent / "fhir" / "schema" / "fhir.schema.json"


@pytest.fixture(scope="module")
def fhir_validator() -> tuple[str, Registry[Any]]:
    schema = json.loads(_SCHEMA_PATH.read_text())
    base_uri = schema["id"]
    resource = Resource.from_contents(schema)
    registry = Registry().with_resource(base_uri, resource)
    return base_uri, registry


def _validate_against(
    resource_type: str,
    document: dict[str, Any],
    fhir_validator: tuple[str, Registry[Any]],
) -> None:
    base_uri, registry = fhir_validator
    pointer_schema = {"$ref": f"{base_uri}#/definitions/{resource_type}"}
    validator = Draft6Validator(pointer_schema, registry=registry)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    assert not errors, "\n".join(f"{list(error.path)}: {error.message}" for error in errors)


@pytest.mark.parametrize("tree_key", SEEDED_TREE_KEYS)
def test_seeded_tree_plan_definition_matches_fhir_r4_schema(
    seeded_session: Session,
    tree_key: str,
    fhir_validator: tuple[str, Registry[Any]],
) -> None:
    available_tree_keys = set(seeded_session.execute(select(DecisionTree.tree_key)).scalars())
    if tree_key not in available_tree_keys:
        pytest.skip(f"seeded tree is not available: {tree_key}")

    graph = SqlAlchemyTreeGraphRepository(seeded_session).get_tree(tree_key)
    plan_definition = PlanDefinition.from_graph(graph)
    document = plan_definition.model_dump(mode="json", by_alias=True, exclude_none=True)

    _validate_against("PlanDefinition", document, fhir_validator)


@pytest.mark.parametrize("tree_key", SEEDED_TREE_KEYS)
def test_seeded_tree_library_matches_fhir_r4_schema_when_present(
    seeded_session: Session,
    tree_key: str,
    fhir_validator: tuple[str, Registry[Any]],
) -> None:
    available_tree_keys = set(seeded_session.execute(select(DecisionTree.tree_key)).scalars())
    if tree_key not in available_tree_keys:
        pytest.skip(f"seeded tree is not available: {tree_key}")

    graph = SqlAlchemyTreeGraphRepository(seeded_session).get_tree(tree_key)
    library = Library.from_graph(graph)
    if library is None:
        pytest.skip(f"tree has no GLOBAL nodes: {tree_key}")

    document = library.model_dump(mode="json", by_alias=True, exclude_none=True)
    _validate_against("Library", document, fhir_validator)


def test_seeded_trees_bundle_matches_fhir_r4_schema(
    seeded_session: Session,
    fhir_validator: tuple[str, Registry[Any]],
) -> None:
    available_tree_keys = set(seeded_session.execute(select(DecisionTree.tree_key)).scalars())
    tree_keys = [key for key in SEEDED_TREE_KEYS if key in available_tree_keys]
    if not tree_keys:
        pytest.skip("no seeded trees available")

    repository = SqlAlchemyTreeGraphRepository(seeded_session)
    plan_definitions = [PlanDefinition.from_graph(repository.get_tree(key)) for key in tree_keys]
    bundle = Bundle.from_plan_definitions(plan_definitions)
    document = bundle.model_dump(mode="json", by_alias=True, exclude_none=True)

    _validate_against("Bundle", document, fhir_validator)
