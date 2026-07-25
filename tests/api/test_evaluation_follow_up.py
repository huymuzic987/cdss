"""API tests for the medication follow-up evaluation endpoint."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from cdss.api.dependencies import get_tree_graph_repository
from cdss.api.schemas.fhir_input import input_to_bundle
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

MEDICATION_FOLLOW_UP_TREE_KEY = "treatment-threshold-and-bp-target"
ESSENTIAL_TREE_KEY = "essential-treatment-strategy"
ACTIVE_BP_TARGET = {
    "sbp": {"upper_exclusive_mmhg": 130},
    "dbp": {"upper_exclusive_mmhg": 80},
    "source": "CALLER_SUPPLIED",
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
    repository = RecordingRepository([_tree3_graph(), _essential_treatment_graph()])
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


def test_follow_up_restores_caller_supplied_target_and_reports_target_reached(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={
            "input": input_to_bundle(
                {
                    "facility_capability": "LIMITED_RESOURCES",
                    "medication_follow_up_stage": "INITIAL_REGIMEN",
                    "active_bp_target": ACTIVE_BP_TARGET,
                    "current_clinic_sbp": 125,
                    "current_clinic_dbp": 75,
                }
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["treatment"]["bp_target"] == ACTIVE_BP_TARGET
    assert body["traversal_log"][-1]["node_key"] == "target-reached"
    assert api_context.repository.read_tree_keys == [
        MEDICATION_FOLLOW_UP_TREE_KEY,
        ESSENTIAL_TREE_KEY,
    ]


def test_follow_up_reports_target_not_reached(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={
            "input": input_to_bundle(
                {
                    "facility_capability": "LIMITED_RESOURCES",
                    "medication_follow_up_stage": "INITIAL_REGIMEN",
                    "active_bp_target": ACTIVE_BP_TARGET,
                    "current_clinic_sbp": 145,
                    "current_clinic_dbp": 95,
                }
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["traversal_log"][-1]["node_key"] == "target-not-reached"


def test_follow_up_with_unknown_facility_capability_returns_422(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={
            "input": input_to_bundle(
                {
                    "facility_capability": "UNKNOWN_FACILITY",
                    "medication_follow_up_stage": "INITIAL_REGIMEN",
                    "active_bp_target": ACTIVE_BP_TARGET,
                    "current_clinic_sbp": 125,
                    "current_clinic_dbp": 75,
                }
            )
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "no_matching_transition"


_COMPLETE_FOLLOW_UP_INPUT = {
    "facility_capability": "LIMITED_RESOURCES",
    "medication_follow_up_stage": "INITIAL_REGIMEN",
    "active_bp_target": ACTIVE_BP_TARGET,
    "current_clinic_sbp": 1,
    "current_clinic_dbp": 1,
}


@pytest.mark.parametrize(
    "missing_key",
    ["facility_capability", "medication_follow_up_stage", "active_bp_target"],
)
def test_follow_up_bundle_missing_a_required_field_returns_invalid_fhir_input(
    api_context: ApiTestContext,
    missing_key: str,
) -> None:
    incomplete = {k: v for k, v in _COMPLETE_FOLLOW_UP_INPUT.items() if k != missing_key}
    response = api_context.client.post(
        "/evaluate/follow-up",
        json={"input": input_to_bundle(incomplete)},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_fhir_input"
    assert missing_key in body["details"]["reason"]


def test_follow_up_request_missing_input_field_returns_invalid_request(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post("/evaluate/follow-up", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_request"


def _tree3_graph() -> TreeGraph:
    """Mirrors the real Tree 3 medication-follow-up branch: restore the
    caller-supplied active_bp_target into context, then route to the
    facility's treatment-strategy tree."""
    tree = _tree(100, MEDICATION_FOLLOW_UP_TREE_KEY)
    start = _node(tree, 101, "start", NodeType.START)
    restore = _node(
        tree,
        102,
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
    link_essential = _node(
        tree,
        103,
        "link-essential",
        NodeType.LINK,
        condition_definition={"op": "eq", "path": "input.facility_capability", "value": "LIMITED_RESOURCES"},
        link_target_tree_key=ESSENTIAL_TREE_KEY,
    )
    return _graph(
        tree,
        [start, restore, link_essential],
        [
            _edge(tree, 109, start, restore, 1),
            _edge(tree, 110, restore, link_essential, 1),
        ],
    )


def _essential_treatment_graph() -> TreeGraph:
    tree = _tree(200, ESSENTIAL_TREE_KEY)
    start = _node(tree, 201, "start", NodeType.START)
    reached = _node(
        tree,
        202,
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
    not_reached = _node(tree, 203, "target-not-reached", NodeType.END)
    return _graph(
        tree,
        [start, reached, not_reached],
        [
            _edge(tree, 209, start, reached, 1),
            _edge(tree, 210, start, not_reached, 2),
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
