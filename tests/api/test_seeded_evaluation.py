"""Read-only API integration tests against the local seeded PostgreSQL database."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
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
PREGNANCY_PRESET_DIR = Path(__file__).parents[2] / "data" / "fhir" / "pregnancy_presets"


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
    orders = body["actions"][-1]["payload"]["presentation"]["recommended_orders"]
    assert orders
    assert all(order["drug_classes"] for order in orders)
    assert all(drug_class["medicines"] for order in orders for drug_class in order["drug_classes"])
    assert body["input_snapshot"]["resourceType"] == "Bundle"
    assert body["references"]


def test_seeded_pregnancy_third_follow_up_reaches_postpartum_branch(
    seeded_api_context: SeededApiContext,
) -> None:
    response = _post_read_only(
        seeded_api_context,
        bundle=_pregnancy_follow_up_bundle(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["inferred_follow_up_type"] == "PREGNANCY_FOLLOW_UP"
    assert body["pregnancy_follow_up"] == {
        "episode_id": "pregnancy-demo-001",
        "encounter_count": 4,
        "follow_up_number": 3,
        "phase": "FOLLOW_UP_3",
        "minimum_follow_ups_required": 3,
        "minimum_follow_ups_completed": True,
        "next_follow_up_number": 4,
        "next_follow_up_required": True,
        "previous_visit_date": "2026-02-16",
    }
    entered = {
        (entry["tree_key"], entry["node_key"])
        for entry in body["traversal_log"]
        if entry["event"] == "node_entered"
    }
    assert ("hypertension-in-pregnancy", "T12_C_POSTPARTUM") in entered
    assert not any(tree_key == "hypertension-diagnosis" for tree_key, _ in entered)
    assert body["actions"][-1]["node_key"] == "T12_END_MAINTAIN_REGIMEN_POSTPARTUM"


@pytest.mark.parametrize(
    ("preset_name", "entry_node", "expected_node", "expected_terminal"),
    [
        (
            "02-pregnancy-high-preeclampsia-risk-aspirin.json",
            "T12_C_CURRENTLY_PREGNANT",
            "T12_C_HIGH_PREECLAMPSIA_RISK",
            "T12_END_ASPIRIN_PROPHYLAXIS",
        ),
        (
            "17-pregnancy-postpartum-bp-normal.json",
            "T12_C_POSTPARTUM",
            "T12_C_BP_NOT_HIGH",
            "T12_END_MAINTAIN_REGIMEN_POSTPARTUM",
        ),
    ],
)
def test_seeded_pregnancy_follow_up_resumes_at_status_branch(
    seeded_api_context: SeededApiContext,
    preset_name: str,
    entry_node: str,
    expected_node: str,
    expected_terminal: str,
) -> None:
    bundle = json.loads((PREGNANCY_PRESET_DIR / preset_name).read_text(encoding="utf-8"))

    response = _post_read_only(seeded_api_context, bundle=bundle)

    assert response.status_code == 200
    body = response.json()
    assert body["inferred_follow_up_type"] == "PREGNANCY_FOLLOW_UP"
    entered = [
        entry["node_key"]
        for entry in body["traversal_log"]
        if entry["event"] == "node_entered" and entry["tree_key"] == "hypertension-in-pregnancy"
    ]
    assert entered[0] == entry_node
    assert expected_node in entered
    assert entered[-1] == expected_terminal


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


def _pregnancy_follow_up_bundle() -> dict[str, Any]:
    patient_id = "pregnancy-follow-up-demo"
    dates_and_bp = (
        ("initial", "2026-01-05", 150, 95),
        ("follow-up-1", "2026-01-26", 140, 85),
        ("follow-up-2", "2026-02-16", 140, 85),
        ("follow-up-3", "2026-03-09", 142, 92),
    )
    input_prefix = "http://cdss.local/fhir/StructureDefinition/input/"
    entries: list[dict[str, Any]] = [
        {
            "resource": {
                "resourceType": "Patient",
                "id": patient_id,
                "birthDate": "1997-01-01",
                "extension": [
                    {
                        "url": f"{input_prefix}pregnancy_episode_id",
                        "valueString": "pregnancy-demo-001",
                    },
                    {
                        "url": f"{input_prefix}pregnancy_follow_up_number",
                        "valueInteger": 3,
                    },
                    {"url": f"{input_prefix}weeks_resolved_postpartum", "valueInteger": 2},
                    {"url": f"{input_prefix}weeks_persisting_postpartum", "valueInteger": 0},
                ],
            }
        },
        {"resource": _clinical_flag(patient_id, "is_postpartum")},
        {"resource": _clinical_flag(patient_id, "is_breastfeeding")},
        {"resource": _clinical_flag(patient_id, "has_hypertension_after_week_20")},
        {
            "resource": _bp(
                patient_id,
                None,
                "home-sbp",
                "8459-0",
                138,
                reading_role="home",
            )
        },
        {
            "resource": _bp(
                patient_id,
                None,
                "home-dbp",
                "8462-4",
                87,
                reading_role="home",
            )
        },
        {"resource": _lab(patient_id, "proteinuria", "2889-4", 50, "mg")},
        {"resource": _lab(patient_id, "acr", "9318-7", 5, "mg/mmol")},
    ]
    for encounter_id, started, sbp, dbp in dates_and_bp:
        entries.extend(
            [
                {"resource": _encounter(patient_id, encounter_id, started)},
                {
                    "resource": _bp(
                        patient_id,
                        encounter_id,
                        f"{encounter_id}-sbp",
                        "8459-0",
                        sbp,
                    )
                },
                {
                    "resource": _bp(
                        patient_id,
                        encounter_id,
                        f"{encounter_id}-dbp",
                        "8462-4",
                        dbp,
                    )
                },
            ]
        )
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def _clinical_flag(patient_id: str, code: str) -> dict[str, Any]:
    return {
        "resourceType": "Condition",
        "id": f"{patient_id}-{code}",
        "subject": {"reference": f"Patient/{patient_id}"},
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://cdss.local/fhir/CodeSystem/clinical-flag",
                    "code": code,
                }
            ]
        },
    }


def _lab(
    patient_id: str,
    observation_id: str,
    code: str,
    value: int,
    unit: str,
) -> dict[str, Any]:
    return {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": code}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {"value": value, "unit": unit},
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
    *,
    reading_role: str | None = None,
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
    if reading_role is not None:
        resource["extension"] = [
            {
                "url": "http://cdss.local/fhir/StructureDefinition/reading-role",
                "valueCode": reading_role,
            }
        ]
    return resource
