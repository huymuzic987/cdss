"""API tests for read-only tree-graph inspection endpoints."""

from __future__ import annotations

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
    repository = RecordingRepository([_routing_graph()])
    app = create_app()
    app.dependency_overrides[get_tree_graph_repository] = lambda: repository
    with TestClient(app) as client:
        yield ApiTestContext(client=client, repository=repository)


def test_list_trees_returns_summaries(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/trees")

    assert response.status_code == 200
    assert response.json() == [
        {"tree_key": "routing-tree", "name_en": "routing-tree", "name_vi": "routing-tree"},
    ]


def test_get_tree_graph_returns_nodes_edges_globals_and_references(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.get("/trees/routing-tree/graph")

    assert response.status_code == 200
    body = response.json()

    assert body["tree"] == {
        "tree_key": "routing-tree",
        "name_en": "routing-tree",
        "name_vi": "routing-tree",
    }
    assert body["start_node_key"] == "start"

    nodes_by_key = {node["node_key"]: node for node in body["nodes"]}
    assert set(nodes_by_key) == {"start", "check-facility", "link-to-other-tree"}

    condition_node = nodes_by_key["check-facility"]
    assert condition_node["node_type"] == "CONDITION"
    assert condition_node["condition_definition"] == {
        "path": "input.facility_capability",
        "op": "eq",
        "value": "full",
    }

    link_node = nodes_by_key["link-to-other-tree"]
    assert link_node["node_type"] == "LINK"
    assert link_node["link_target_tree_key"] == "other-tree"
    assert link_node["link_target_node_key"] == "other-start"

    assert {(edge["from_node_key"], edge["to_node_key"]) for edge in body["edges"]} == {
        ("start", "check-facility"),
        ("check-facility", "link-to-other-tree"),
    }

    assert body["global_nodes"] == [
        {
            "node_key": "global-config",
            "text_en": "global-config",
            "text_vi": "global-config",
            "global_config": {"note": "audited"},
            "display_order": 900,
        }
    ]

    assert body["references"] == [
        {
            "node_key": "check-facility",
            "source_title": "Guideline",
            "section_path": [{"number": "4.2", "title": "Facility routing"}],
            "reference_order": 0,
            "locator": "p42",
            "locator_detail": None,
            "reference_note": None,
        }
    ]


def test_get_tree_graph_missing_tree_returns_404(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/trees/missing-tree/graph")

    assert response.status_code == 404
    assert response.json()["code"] == "tree_not_found"


def _routing_graph() -> TreeGraph:
    tree = _tree(300, "routing-tree")
    start = _node(tree, 301, "start", NodeType.START)
    condition = _node(
        tree,
        302,
        "check-facility",
        NodeType.CONDITION,
        condition_definition={"path": "input.facility_capability", "op": "eq", "value": "full"},
    )
    link = _node(
        tree,
        303,
        "link-to-other-tree",
        NodeType.LINK,
        link_target_tree_key="other-tree",
        link_target_node_key="other-start",
    )
    global_node = _node(
        tree,
        304,
        "global-config",
        NodeType.GLOBAL,
        global_config={"note": "audited"},
        display_order=900,
    )
    reference = SourceReferenceDefinition(
        id=UUID(int=310),
        node_id=condition.id,
        source_title="Guideline",
        section_path=[{"number": "4.2", "title": "Facility routing"}],
        reference_order=0,
        locator="p42",
    )
    return TreeGraph.build(
        tree=tree,
        nodes=[start, condition, link, global_node],
        edges=[
            _edge(tree, 320, start, condition),
            _edge(tree, 321, condition, link),
        ],
        references=[reference],
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
        display_order=values.pop("display_order", serial),
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
