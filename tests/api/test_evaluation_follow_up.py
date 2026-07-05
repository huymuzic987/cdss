"""API tests for the derive-then-compare follow-up evaluation endpoint."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from cdss.api.dependencies import get_tree_graph_repository
from cdss.core.config import Settings, get_settings
from cdss.domain.decision_tree import (
    EdgeDefinition,
    NodeDefinition,
    NodeType,
    TreeDefinition,
    TreeGraph,
    TreeNotFound,
)
from cdss.main import create_app

DIAGNOSIS_TREE_KEY = "hypertension-diagnosis"
ESSENTIAL_TREE_KEY = "essential-treatment-strategy"
DERIVED_BP_TARGET = {
    "sbp": {"upper_exclusive_mmhg": 130},
    "dbp": {"upper_exclusive_mmhg": 80},
    "source": "DERIVED_FROM_DIAGNOSIS_FACTS",
}


class RecordingRepository:
    def __init__(self, graphs: list[TreeGraph]) -> None:
        self.graphs = {graph.tree.tree_key: graph for graph in graphs}
        self.read_tree_keys: list[str] = []

    def get_tree(self, tree_key: str) -> TreeGraph:
        self.read_tree_keys.append(tree_key)
        try:
            return self.graphs[tree_key]
        except KeyError as exc:
            raise TreeNotFound(tree_key=tree_key) from exc


@dataclass
class ApiTestContext:
    client: TestClient
    repository: RecordingRepository


@pytest.fixture
def api_context() -> Iterator[ApiTestContext]:
    repository = RecordingRepository([_diagnosis_graph(), _essential_treatment_graph()])
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        database_url="postgresql://unused:unused@127.0.0.1:1/unused",
    )
    app = create_app()
    app.dependency_overrides[get_tree_graph_repository] = lambda: repository
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield ApiTestContext(client=client, repository=repository)


def test_follow_up_derives_target_then_reports_target_reached(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={
            "diagnosis_input": {
                # Deliberately claims to be a follow-up; the endpoint must
                # force is_medication_follow_up=false for the derivation call
                # so it re-derives the target instead of trying to restore one.
                "is_medication_follow_up": True,
            },
            "facility_capability": "LIMITED_RESOURCES",
            "medication_follow_up_stage": "INITIAL_REGIMEN",
            "current_clinic_sbp": 125,
            "current_clinic_dbp": 75,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["active_bp_target"] == DERIVED_BP_TARGET
    assert body["derivation"]["context"]["treatment"]["bp_target"] == DERIVED_BP_TARGET
    assert body["comparison"]["context"]["treatment"]["bp_target"] == DERIVED_BP_TARGET
    assert body["comparison"]["traversal_log"][-1]["node_key"] == "target-reached"
    assert api_context.repository.read_tree_keys == [DIAGNOSIS_TREE_KEY, ESSENTIAL_TREE_KEY]


def test_follow_up_reports_target_not_reached(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={
            "diagnosis_input": {},
            "facility_capability": "LIMITED_RESOURCES",
            "medication_follow_up_stage": "INITIAL_REGIMEN",
            "current_clinic_sbp": 145,
            "current_clinic_dbp": 95,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["comparison"]["traversal_log"][-1]["node_key"] == "target-not-reached"


def test_follow_up_without_derived_target_returns_422(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={
            "diagnosis_input": {"normotensive": True},
            "facility_capability": "LIMITED_RESOURCES",
            "medication_follow_up_stage": "INITIAL_REGIMEN",
            "current_clinic_sbp": 125,
            "current_clinic_dbp": 75,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "missing_runtime_path"
    assert body["details"]["reason"] == "bp_target_not_derived"


def test_follow_up_with_unknown_facility_capability_returns_422(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={
            "diagnosis_input": {},
            "facility_capability": "UNKNOWN_FACILITY",
            "medication_follow_up_stage": "INITIAL_REGIMEN",
            "current_clinic_sbp": 125,
            "current_clinic_dbp": 75,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "missing_runtime_path"
    assert body["details"]["reason"] == "unknown_facility_capability"


@pytest.mark.parametrize(
    "payload",
    [
        {"facility_capability": "LIMITED_RESOURCES", "medication_follow_up_stage": "INITIAL_REGIMEN", "current_clinic_sbp": 1, "current_clinic_dbp": 1},
        {"diagnosis_input": {}, "medication_follow_up_stage": "INITIAL_REGIMEN", "current_clinic_sbp": 1, "current_clinic_dbp": 1},
    ],
)
def test_malformed_follow_up_request_returns_stable_validation_error(
    api_context: ApiTestContext,
    payload: object,
) -> None:
    response = api_context.client.post("/evaluate/follow-up", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_request"


def _diagnosis_graph() -> TreeGraph:
    tree = _tree(100, DIAGNOSIS_TREE_KEY)
    start = _node(tree, 101, "start", NodeType.START)
    normal_bp = _node(
        tree,
        102,
        "normal-bp",
        NodeType.END,
        condition_definition={"op": "exists", "path": "input.normotensive"},
    )
    restore = _node(
        tree,
        103,
        "restore-target-should-not-run",
        NodeType.END,
        condition_definition={
            "all": [{"op": "eq", "path": "input.is_medication_follow_up", "value": True}]
        },
        context_patch={"treatment": {"bp_target": {"source": "SHOULD_NOT_BE_USED"}}},
    )
    derive = _node(
        tree,
        104,
        "derive-target",
        NodeType.END,
        condition_definition={
            "all": [{"op": "eq", "path": "input.is_medication_follow_up", "value": False}]
        },
        context_patch={"treatment": {"bp_target": DERIVED_BP_TARGET}},
    )
    return _graph(
        tree,
        [start, normal_bp, restore, derive],
        [
            _edge(tree, 109, start, normal_bp, 1),
            _edge(tree, 110, start, restore, 2),
            _edge(tree, 111, start, derive, 3),
        ],
    )


def _essential_treatment_graph() -> TreeGraph:
    tree = _tree(200, ESSENTIAL_TREE_KEY)
    start = _node(tree, 201, "start", NodeType.START)
    restore = _node(
        tree,
        202,
        "restore-active-bp-target",
        NodeType.INFERENCE,
        context_patch={
            "operations": [
                {
                    "op": "COPY_PATH",
                    "to_path": "context.treatment.bp_target",
                    "from_path": "input.active_bp_target",
                    "required": True,
                }
            ]
        },
    )
    reached = _node(
        tree,
        203,
        "target-reached",
        NodeType.END,
        condition_definition={
            "all": [
                {
                    "op": "lt",
                    "path": "input.current_clinic_sbp",
                    "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg",
                },
                {
                    "op": "lt",
                    "path": "input.current_clinic_dbp",
                    "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg",
                },
            ]
        },
    )
    not_reached = _node(tree, 204, "target-not-reached", NodeType.END)
    return _graph(
        tree,
        [start, restore, reached, not_reached],
        [
            _edge(tree, 209, start, restore, 1),
            _edge(tree, 210, restore, reached, 1),
            _edge(tree, 211, restore, not_reached, 2),
        ],
    )


def _tree(serial: int, tree_key: str) -> TreeDefinition:
    return TreeDefinition(
        id=UUID(int=serial),
        tree_key=tree_key,
        name_en=tree_key,
        name_vi=tree_key,
    )


def _node(
    tree: TreeDefinition,
    serial: int,
    node_key: str,
    node_type: NodeType,
    **values: Any,
) -> NodeDefinition:
    return NodeDefinition(
        id=UUID(int=serial),
        tree_id=tree.id,
        node_key=node_key,
        node_type=node_type,
        text_en=node_key,
        text_vi=node_key,
        display_order=serial,
        **values,
    )


def _edge(
    tree: TreeDefinition,
    serial: int,
    source: NodeDefinition,
    target: NodeDefinition,
    traversal_order: int,
) -> EdgeDefinition:
    return EdgeDefinition(
        id=UUID(int=serial),
        from_node_id=source.id,
        to_node_id=target.id,
        traversal_order=traversal_order,
        from_tree_id=tree.id,
        to_tree_id=tree.id,
    )


def _graph(
    tree: TreeDefinition,
    nodes: list[NodeDefinition],
    edges: list[EdgeDefinition],
) -> TreeGraph:
    return TreeGraph.build(tree=tree, nodes=nodes, edges=edges, references=[])
