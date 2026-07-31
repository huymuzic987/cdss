"""Read-only API integration tests against the local seeded PostgreSQL database."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_tree_graph_repository
from cdss.core.config import Settings, get_settings
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository
from cdss.infrastructure.db.models import (
    DecisionEdge,
    DecisionNode,
    DecisionTree,
    DevelopmentRuntimeLog,
    NodeSourceReference,
)
from cdss.main import create_app
from cdss.testing.database import TestDatabaseTarget as DatabaseTarget

pytestmark = pytest.mark.database

T1 = "hypertension-diagnosis"
T3 = "treatment-threshold-and-bp-target"
T5 = "optimal-treatment-strategy"
MAINTAIN_REGIMEN_TEXT_VI = "Tiếp tục theo dõi và duy trì phác đồ"

ACTIVE_BP_TARGET = {
    "dbp": {"upper_exclusive_mmhg": 80},
    "sbp": {
        "lower_reference_mmhg": 120,
        "or_lower": True,
        "upper_exclusive_mmhg": 140,
    },
    "source": "TREE_3_GENERIC",
}


@dataclass(frozen=True)
class SeededApiContext:
    client: TestClient
    session: Session


@pytest.fixture(scope="module")
def seeded_api_context(
    seeded_session: Session,
    seeded_database_target: DatabaseTarget,
) -> Iterator[SeededApiContext]:
    repository = SqlAlchemyTreeGraphRepository(seeded_session)
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        database_url=seeded_database_target.database_url,
    )
    app = create_app()
    app.dependency_overrides[get_tree_graph_repository] = lambda: repository
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield SeededApiContext(client=client, session=seeded_session)


def test_seeded_tree_1_normal_bp_is_read_only(seeded_api_context: SeededApiContext) -> None:
    response = _post_read_only(
        seeded_api_context,
        bundle=_initial_bundle(sbp=120, dbp=80),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["context"]["diagnosis"]["hypertension_class"] == "NORMAL_BP"
    assert [
        (action["tree_key"], action["node_key"], action["node_type"]) for action in body["actions"]
    ] == [(T1, "T1_END_ESSENTIAL_NORMAL_BP", "END")]
    assert body["traversal_log"][-1]["node_key"] == "T1_END_ESSENTIAL_NORMAL_BP"
    assert body["references"]


def test_seeded_tree_5_target_reached_is_read_only(
    seeded_api_context: SeededApiContext,
) -> None:
    response = _post_read_only(
        seeded_api_context,
        bundle=_medication_bundle(current_sbp=129, current_dbp=79),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["context"]["treatment"]["bp_target"] == ACTIVE_BP_TARGET
    assert any(
        entry["tree_key"] == T3 and entry["node_key"] == "T3_LINK_OPTIMAL_TREATMENT_STRATEGY"
        for entry in body["traversal_log"]
    )
    assert any(entry["tree_key"] == T5 for entry in body["traversal_log"])
    assert [action["text_vi"] for action in body["actions"]] == [MAINTAIN_REGIMEN_TEXT_VI]
    assert body["references"]


def test_seeded_drug_combination_uses_closed_world_clinical_defaults(
    seeded_api_context: SeededApiContext,
) -> None:
    response = _post_read_only(
        seeded_api_context,
        bundle=_medication_bundle(current_sbp=140, current_dbp=80),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["context"]["treatment"]["bp_target"] == ACTIVE_BP_TARGET
    assert any(entry["tree_key"] == "drug-combination" for entry in body["traversal_log"])
    assert body["input_snapshot"]["resourceType"] == "Bundle"
    assert body["references"]


def _post_read_only(
    context: SeededApiContext,
    *,
    bundle: dict[str, Any],
):
    before = _database_row_counts(context.session)
    response = context.client.post(
        "/evaluate",
        json=bundle,
    )
    assert _database_row_counts(context.session) == before
    return response


def _database_row_counts(session: Session) -> dict[str, int]:
    models = (
        DecisionTree,
        DecisionNode,
        DecisionEdge,
        NodeSourceReference,
        DevelopmentRuntimeLog,
    )
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
        for model in models
    }


def _initial_bundle(*, sbp: int, dbp: int) -> dict[str, Any]:
    patient_id = "seeded-api-patient"
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": patient_id}},
            {"resource": _bp(patient_id, None, "clinic-sbp", "8459-0", sbp)},
            {"resource": _bp(patient_id, None, "clinic-dbp", "8462-4", dbp)},
        ],
    }


def _medication_bundle(*, current_sbp: int, current_dbp: int) -> dict[str, Any]:
    patient_id = "seeded-api-follow-up"
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": patient_id,
                    "birthDate": "1980-01-01",
                }
            },
            {"resource": _encounter(patient_id, "previous", "2026-01-01")},
            {"resource": _encounter(patient_id, "current", "2026-02-01")},
            {"resource": _bp(patient_id, "previous", "previous-sbp", "8459-0", 150)},
            {"resource": _bp(patient_id, "previous", "previous-dbp", "8462-4", 95)},
            {"resource": _bp(patient_id, "current", "current-sbp", "8459-0", current_sbp)},
            {"resource": _bp(patient_id, "current", "current-dbp", "8462-4", current_dbp)},
        ],
    }


def _encounter(patient_id: str, encounter_id: str, start: str) -> dict[str, Any]:
    extensions = []
    if encounter_id == "current":
        extensions.append(
            {
                "url": "http://cdss.local/fhir/StructureDefinition/facility-capability",
                "valueString": "FULL_RESOURCES",
            }
        )
    return {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {"start": start},
        "extension": extensions,
    }


def _bp(
    patient_id: str,
    encounter_id: str | None,
    observation_id: str,
    code: str,
    value: int,
) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": code}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {"value": value, "unit": "mmHg"},
    }
    if encounter_id is not None:
        resource["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    return resource
