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
        "upper_exclusive_mmhg": 130,
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
        tree_key=T1,
        runtime_input={
            "clinic_1_sbp": 120,
            "clinic_1_dbp": 80,
            "clinic_2_sbp": 120,
            "clinic_2_dbp": 80,
            "clinic_3_sbp": 120,
            "clinic_3_dbp": 80,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["context"]["diagnosis"]["hypertension_class"] == "NORMAL_BP"
    assert body["actions"] == []
    assert body["traversal_log"][-1]["node_key"] == "T1_END_ESSENTIAL_NORMAL_BP"
    assert body["references"]


def test_seeded_tree_5_target_reached_is_read_only(
    seeded_api_context: SeededApiContext,
) -> None:
    response = _post_read_only(
        seeded_api_context,
        tree_key=T3,
        runtime_input=_medication_input(current_sbp=129, current_dbp=79),
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


def test_seeded_drug_combination_failure_preserves_partial_state_read_only(
    seeded_api_context: SeededApiContext,
) -> None:
    response = _post_read_only(
        seeded_api_context,
        tree_key=T3,
        runtime_input=_medication_input(current_sbp=130, current_dbp=80),
    )

    assert response.status_code == 424
    body = response.json()
    assert body["code"] == "link_target_not_found"
    assert body["details"]["link_target_tree_key"] == "drug-combination"
    partial = body["partial_run_state"]
    assert partial["context"]["treatment"]["bp_target"] == ACTIVE_BP_TARGET
    assert partial["actions"][-1]["node_key"] == "T5_ACTION_FIXED_DOSE_THREE_DRUG_COMBINATION"
    assert partial["traversal_log"][-1]["node_key"] == "T5_LINK_THREE_DRUG_TO_TREE_6"
    assert partial["references"]


def _post_read_only(
    context: SeededApiContext,
    *,
    tree_key: str,
    runtime_input: dict[str, Any],
):
    before = _database_row_counts(context.session)
    response = context.client.post(
        "/evaluate",
        json={"start_tree_key": tree_key, "input": runtime_input},
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


def _medication_input(*, current_sbp: int, current_dbp: int) -> dict[str, Any]:
    return {
        "is_medication_follow_up": True,
        "facility_capability": "FULL_RESOURCES",
        "medication_follow_up_stage": "INITIAL_REGIMEN",
        "active_bp_target": ACTIVE_BP_TARGET,
        "current_clinic_sbp": current_sbp,
        "current_clinic_dbp": current_dbp,
    }
