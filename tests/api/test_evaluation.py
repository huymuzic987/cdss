"""API tests for stateless decision-tree evaluation."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
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


class RecordingRepository:
    def __init__(self, graphs: list[TreeGraph]) -> None:
        self.graphs = {graph.tree.tree_key: graph for graph in graphs}
        self.read_tree_keys: list[str] = []
        self.persisted_patient_data: list[object] = []

    def get_tree(self, tree_key: str) -> TreeGraph:
        self.read_tree_keys.append(tree_key)
        try:
            return self.graphs[tree_key]
        except KeyError as exc:
            raise TreeNotFound(tree_key=tree_key) from exc

    def persist_patient(self, patient_data: object) -> None:
        self.persisted_patient_data.append(patient_data)


@dataclass
class ApiTestContext:
    client: TestClient
    repository: RecordingRepository


@pytest.fixture
def api_context() -> Iterator[ApiTestContext]:
    repository = RecordingRepository([_normal_bp_graph(), _unresolved_link_graph()])
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


def test_tree_1_essential_normal_bp_result(api_context: ApiTestContext) -> None:
    bundle = _canonical_bundle()
    response = api_context.client.post("/evaluate", json=bundle)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "status",
        "input_snapshot",
        "context",
        "actions",
        "traversal_log",
        "references",
        "tree_metadata",
        "started_at",
        "completed_at",
        "inferred_follow_up_type",
        "previous_recommended_action_types",
    }
    assert body["status"] == "success"
    assert body["context"]["diagnosis"]["hypertension_class"] == "NORMAL_BP"
    assert body["input_snapshot"] == bundle
    assert body["actions"][-1]["payload"]["presentation"]["schema_version"] == "1.0"
    assert body["traversal_log"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"input": {}},
        {"start_tree_key": "hypertension-diagnosis", "input": []},
        [],
    ],
)
def test_malformed_input_returns_stable_validation_error(
    api_context: ApiTestContext,
    payload: object,
) -> None:
    response = api_context.client.post("/evaluate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] in {"invalid_request", "invalid_fhir_input"}
    assert "traceback" not in body


def test_non_bundle_input_returns_invalid_fhir_input(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/evaluate",
        json={"foo": "bar"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_fhir_input"
    assert "traceback" not in body


def test_non_bundle_input_returns_invalid_fhir_input(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/evaluate",
        json={"start_tree_key": "hypertension-diagnosis", "input": {"foo": "bar"}},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_fhir_input"
    assert "traceback" not in body


def test_tree_not_found_returns_404(api_context: ApiTestContext) -> None:
    del api_context.repository.graphs["hypertension-diagnosis"]
    response = api_context.client.post("/evaluate", json=_canonical_bundle())

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "tree_not_found"
    assert body["message"] == "Decision tree 'hypertension-diagnosis' was not found."
    assert body["tree_key"] == "hypertension-diagnosis"
    assert body["node_key"] is None
    assert body["details"] == {}
    assert body["partial_run_state"] is None


def test_unresolved_link_returns_424_with_partial_execution_state(
    api_context: ApiTestContext,
) -> None:
    api_context.repository.graphs["hypertension-diagnosis"] = _unresolved_link_graph()
    response = api_context.client.post("/evaluate", json=_canonical_bundle())

    assert response.status_code == 424
    body = response.json()
    assert body["code"] == "link_target_not_found"
    assert body["details"]["link_target_tree_key"] == "external-tree"
    partial = body["partial_run_state"]
    assert partial["input_snapshot"]["resourceType"] == "Bundle"
    assert partial["context"]["prepared"] is True
    assert partial["context"]["diagnosis"] == {
        "current_clinic_sbp": 128.0,
        "current_clinic_dbp": 80.0,
    }
    assert [action["payload"] for action in partial["actions"]] == [{"recommendation": "prepare"}]
    assert partial["traversal_log"][-1]["node_key"] == "external-link"
    assert "traceback" not in body


def test_evaluate_stops_at_generic_action_even_when_it_has_outgoing_edges(
    api_context: ApiTestContext,
) -> None:
    api_context.repository.graphs["hypertension-diagnosis"] = _multi_action_graph()

    response = api_context.client.post(
        "/evaluate",
        json=_canonical_bundle(),
    )

    assert response.status_code == 200
    body = response.json()
    assert [a["node_key"] for a in body["actions"]] == ["intermediate-1"]
    assert [e["node_key"] for e in body["traversal_log"] if e["event"] == "node_entered"] == [
        "start",
        "intermediate-1",
    ]


def test_debug_output_does_not_bypass_generic_action_termination() -> None:
    graph = _multi_action_graph()
    repository = RecordingRepository([graph])
    repository.graphs["hypertension-diagnosis"] = graph
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        database_url="postgresql://unused:unused@127.0.0.1:1/unused",
        debug_output=True,
    )
    app = create_app()
    app.dependency_overrides[get_tree_graph_repository] = lambda: repository
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        response = client.post(
            "/evaluate",
            json=_canonical_bundle(),
        )

    assert response.status_code == 200
    body = response.json()
    assert [a["node_key"] for a in body["actions"]] == ["intermediate-1"]


def test_request_completion_does_not_persist_patient_data(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post("/evaluate", json=_canonical_bundle())

    assert response.status_code == 200
    assert api_context.repository.persisted_patient_data == []
    assert api_context.repository.read_tree_keys[-1] == "hypertension-diagnosis"


def _canonical_bundle() -> dict[str, Any]:
    path = Path(__file__).parents[2] / "data" / "fhir" / "test_case" / "PT0001.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _normal_bp_graph() -> TreeGraph:
    tree = _tree(100, "hypertension-diagnosis")
    start = _node(tree, 101, "start", NodeType.START)
    end = _node(
        tree,
        102,
        "normal-bp",
        NodeType.END,
        context_patch={"diagnosis": {"hypertension_class": "NORMAL_BP"}},
    )
    return _graph(tree, [start, end], [_edge(tree, 110, start, end)])


def _multi_action_graph() -> TreeGraph:
    """Mirrors drug-combination's shape: several non-terminal ACTION nodes
    (each recording an intermediate step) chained before the terminal END."""
    tree = _tree(300, "multi-action-tree")
    start = _node(tree, 301, "start", NodeType.START)
    intermediate_1 = _node(
        tree,
        302,
        "intermediate-1",
        NodeType.ACTION,
        action_payload={"action_type": "CHECK_DUPLICATE_DRUG_CLASS"},
    )
    intermediate_2 = _node(
        tree,
        303,
        "intermediate-2",
        NodeType.ACTION,
        action_payload={"action_type": "MAINTAIN_CURRENT_REGIMEN"},
    )
    final = _node(
        tree,
        304,
        "final",
        NodeType.END,
        action_payload={"action_type": "INITIAL_TWO_DRUG_COMBINATION"},
    )
    return _graph(
        tree,
        [start, intermediate_1, intermediate_2, final],
        [
            _edge(tree, 310, start, intermediate_1),
            _edge(tree, 311, intermediate_1, intermediate_2),
            _edge(tree, 312, intermediate_2, final),
        ],
    )


def _unresolved_link_graph() -> TreeGraph:
    tree = _tree(200, "essential-treatment-strategy")
    start = _node(tree, 201, "start", NodeType.START)
    action = _node(
        tree,
        202,
        "prepare",
        NodeType.ACTION,
        action_payload={"recommendation": "prepare"},
        context_patch={"prepared": True},
    )
    link = _node(
        tree,
        203,
        "external-link",
        NodeType.LINK,
        link_target_tree_key="external-tree",
    )
    return _graph(
        tree,
        [start, action, link],
        [_edge(tree, 210, start, action), _edge(tree, 211, action, link)],
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
) -> EdgeDefinition:
    return EdgeDefinition(
        id=UUID(int=serial),
        from_node_id=source.id,
        to_node_id=target.id,
        traversal_order=1,
        from_tree_id=tree.id,
        to_tree_id=tree.id,
    )


def _graph(
    tree: TreeDefinition,
    nodes: list[NodeDefinition],
    edges: list[EdgeDefinition],
) -> TreeGraph:
    return TreeGraph.build(tree=tree, nodes=nodes, edges=edges, references=[])
