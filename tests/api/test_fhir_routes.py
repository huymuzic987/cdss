"""API tests for the read-only HL7 FHIR R4 export endpoints."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from cdss.api.dependencies import get_tree_graph_repository
from cdss.domain.decision_tree import (
    EdgeDefinition,
    NodeDefinition,
    NodeType,
    SourceReferenceDefinition,
    TreeDefinition,
    TreeGraph,
    TreeNotFound,
)
from cdss.main import create_app


class RecordingRepository:
    def __init__(self, graphs: list[TreeGraph]) -> None:
        self.graphs = {graph.tree.tree_key: graph for graph in graphs}

    def get_tree(self, tree_key: str) -> TreeGraph:
        try:
            return self.graphs[tree_key]
        except KeyError as exc:
            raise TreeNotFound(tree_key=tree_key) from exc

    def list_trees(self) -> Sequence[TreeDefinition]:
        return [graph.tree for graph in self.graphs.values()]


@dataclass
class ApiTestContext:
    client: TestClient
    repository: RecordingRepository


@pytest.fixture
def api_context() -> Iterator[ApiTestContext]:
    repository = RecordingRepository([_full_graph(), _no_global_graph()])
    app = create_app()
    app.dependency_overrides[get_tree_graph_repository] = lambda: repository
    with TestClient(app) as client:
        yield ApiTestContext(client=client, repository=repository)


def test_list_plan_definitions_returns_bundle(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/fhir/PlanDefinition")

    assert response.status_code == 200
    body = response.json()
    assert body["resourceType"] == "Bundle"
    assert body["type"] == "searchset"
    resource_ids = {entry["resource"]["id"] for entry in body["entry"]}
    assert resource_ids == {"full-tree", "no-global-tree"}
    for entry in body["entry"]:
        assert entry["fullUrl"] == f"PlanDefinition/{entry['resource']['id']}"
        assert entry["resource"]["resourceType"] == "PlanDefinition"


def test_get_plan_definition_maps_all_node_types_and_edges(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.get("/fhir/PlanDefinition/full-tree")

    assert response.status_code == 200
    body = response.json()

    assert body["resourceType"] == "PlanDefinition"
    assert body["id"] == "full-tree"
    assert body["status"] == "active"
    assert body["library"] == ["Library/full-tree-config"]

    actions_by_id = {action["id"]: action for action in body["action"]}
    assert set(actions_by_id) == {
        "start",
        "check-facility",
        "infer-risk",
        "record-action",
        "end",
        "link-with-target",
        "link-without-target",
    }

    condition_action = actions_by_id["check-facility"]
    assert condition_action["code"] == [
        {"coding": [{"system": "http://cdss.local/fhir/CodeSystem/node-type", "code": "CONDITION"}]}
    ]
    assert condition_action["condition"] == [
        {
            "kind": "applicability",
            "expression": {
                "language": "text/fhirpath",
                "expression": "(%input.facility_capability = 'full')",
            },
        }
    ]
    condition_source_ext = next(
        ext
        for ext in condition_action["extension"]
        if ext["url"] == "http://cdss.local/fhir/StructureDefinition/condition-definition-source"
    )
    assert json.loads(condition_source_ext["valueString"]) == {
        "path": "input.facility_capability",
        "op": "eq",
        "value": "full",
    }
    assert condition_action["documentation"] == [
        {"type": "citation", "display": "Guideline (p42)", "citation": "[]"}
    ]

    action_node = actions_by_id["record-action"]
    payload_ext = next(
        ext
        for ext in action_node["extension"]
        if ext["url"] == "http://cdss.local/fhir/StructureDefinition/action-payload"
    )
    assert json.loads(payload_ext["valueString"]) == {"action_type": "CONTINUE_MONITORING"}

    link_with_target = actions_by_id["link-with-target"]
    assert link_with_target["definitionCanonical"] == "PlanDefinition/other-tree"
    link_target_ext = next(
        ext
        for ext in link_with_target["extension"]
        if ext["url"] == "http://cdss.local/fhir/StructureDefinition/link-target-node"
    )
    assert link_target_ext["valueString"] == "other-start"

    link_without_target = actions_by_id["link-without-target"]
    assert link_without_target["definitionCanonical"] == "PlanDefinition/other-tree"
    assert not any(
        ext["url"] == "http://cdss.local/fhir/StructureDefinition/link-target-node"
        for ext in link_without_target.get("extension", [])
    )

    start_action = actions_by_id["start"]
    related_action = start_action["relatedAction"][0]
    assert related_action["actionId"] == "check-facility"
    assert related_action["relationship"] == "before-start"
    traversal_ext = next(
        ext
        for ext in related_action["extension"]
        if ext["url"] == "http://cdss.local/fhir/StructureDefinition/traversal-order"
    )
    assert traversal_ext["valueInteger"] == 1


def test_get_plan_definition_omits_library_when_no_global_nodes(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.get("/fhir/PlanDefinition/no-global-tree")

    assert response.status_code == 200
    assert "library" not in response.json()


def test_get_library_returns_base64_json_content(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/fhir/Library/full-tree")

    assert response.status_code == 200
    body = response.json()
    assert body["resourceType"] == "Library"
    assert body["id"] == "full-tree-config"
    assert body["type"] == {
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/library-type",
                "code": "logic-library",
            }
        ]
    }
    decoded = json.loads(base64.b64decode(body["content"][0]["data"]))
    assert decoded == [
        {
            "node_key": "GLOBAL_CONFIG",
            "text_en": "global-config",
            "text_vi": "global-config",
            "global_config": {"note": "audited"},
        }
    ]


def test_get_library_missing_global_nodes_returns_404(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/fhir/Library/no-global-tree")

    assert response.status_code == 404


def test_get_plan_definition_missing_tree_returns_404(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/fhir/PlanDefinition/missing-tree")

    assert response.status_code == 404
    assert response.json()["code"] == "tree_not_found"


def test_get_library_missing_tree_returns_404(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/fhir/Library/missing-tree")

    assert response.status_code == 404


def _full_graph() -> TreeGraph:
    tree = _tree(400, "full-tree")
    start = _node(tree, 401, "start", NodeType.START)
    condition = _node(
        tree,
        402,
        "check-facility",
        NodeType.CONDITION,
        condition_definition={"path": "input.facility_capability", "op": "eq", "value": "full"},
    )
    inference = _node(tree, 403, "infer-risk", NodeType.INFERENCE)
    action = _node(
        tree,
        404,
        "record-action",
        NodeType.ACTION,
        action_payload={"action_type": "CONTINUE_MONITORING"},
    )
    end = _node(tree, 405, "end", NodeType.END)
    link_with_target = _node(
        tree,
        406,
        "link-with-target",
        NodeType.LINK,
        link_target_tree_key="other-tree",
        link_target_node_key="other-start",
    )
    link_without_target = _node(
        tree,
        407,
        "link-without-target",
        NodeType.LINK,
        link_target_tree_key="other-tree",
    )
    global_node = _node(
        tree,
        408,
        "GLOBAL_CONFIG",
        NodeType.GLOBAL,
        global_config={"note": "audited"},
        display_order=900,
    )
    reference = SourceReferenceDefinition(
        id=UUID(int=410),
        node_id=condition.id,
        source_title="Guideline",
        section_path=[],
        reference_order=0,
        locator="p42",
    )
    return TreeGraph.build(
        tree=tree,
        nodes=[
            start,
            condition,
            inference,
            action,
            end,
            link_with_target,
            link_without_target,
            global_node,
        ],
        edges=[
            _edge(tree, 420, start, condition, traversal_order=1),
            _edge(tree, 421, condition, inference, traversal_order=1),
            _edge(tree, 422, inference, action, traversal_order=1),
            _edge(tree, 423, action, end, traversal_order=1),
        ],
        references=[reference],
    )


def _no_global_graph() -> TreeGraph:
    tree = _tree(500, "no-global-tree")
    start = _node(tree, 501, "start", NodeType.START)
    end = _node(tree, 502, "end", NodeType.END)
    return TreeGraph.build(
        tree=tree,
        nodes=[start, end],
        edges=[_edge(tree, 520, start, end, traversal_order=1)],
        references=[],
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
        text_en=node_key.lower().replace("_", "-"),
        text_vi=node_key.lower().replace("_", "-"),
        display_order=values.pop("display_order", serial),
        **values,
    )


def _edge(
    tree: TreeDefinition,
    serial: int,
    source: NodeDefinition,
    target: NodeDefinition,
    *,
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
