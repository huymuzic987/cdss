"""Database-free tests for the SQLAlchemy tree graph repository."""

from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from cdss.domain.decision_tree import InvalidTreeStructure, TreeNotFound
from cdss.infrastructure.db.decision_tree_repository import (
    SqlAlchemyTreeGraphRepository,
    _coerce_node_type,
)
from cdss.infrastructure.db.models import (
    DecisionEdge,
    DecisionNode,
    DecisionTree,
    NodeSourceReference,
    NodeType,
)


class StubResult:
    def __init__(self, *, scalar: Any = None, rows: Sequence[Any] = ()) -> None:
        self._scalar = scalar
        self._rows = list(rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalars(self) -> StubResult:
        return self

    def all(self) -> list[Any]:
        return self._rows


class ScriptedSession:
    def __init__(self, results: Sequence[StubResult]) -> None:
        self._results = iter(results)
        self.executed_statements: list[Executable] = []

    def execute(self, statement: Executable) -> StubResult:
        self.executed_statements.append(statement)
        return next(self._results)


def test_repository_bulk_loads_valid_graph_in_four_queries() -> None:
    tree_id = UUID(int=1)
    start_id = UUID(int=10)
    action_id = UUID(int=11)
    tree = DecisionTree(
        id=tree_id,
        tree_key="test-tree",
        name_en="Test tree",
        name_vi="Cay thu nghiem",
    )
    start = DecisionNode(
        id=start_id,
        tree_id=tree_id,
        node_key="start",
        node_type=NodeType.START,
        text_en="Start",
        text_vi="Bat dau",
        display_order=1,
    )
    action = DecisionNode(
        id=action_id,
        tree_id=tree_id,
        node_key="action",
        node_type=NodeType.ACTION,
        text_en="Monitor",
        text_vi="Theo doi",
        action_payload={"kind": "monitor"},
        display_order=2,
    )
    edge = DecisionEdge(
        id=UUID(int=20),
        from_node_id=start_id,
        to_node_id=action_id,
        traversal_order=1,
    )
    reference = NodeSourceReference(
        id=UUID(int=30),
        node_id=action_id,
        source_title="Guideline",
        section_path=["section", "1"],
        reference_order=1,
    )
    scripted_session = ScriptedSession(
        [
            StubResult(scalar=tree),
            StubResult(rows=[start, action]),
            StubResult(rows=[(edge, tree_id, tree_id)]),
            StubResult(rows=[reference]),
        ]
    )
    repository = SqlAlchemyTreeGraphRepository(cast(Session, scripted_session))

    graph = repository.get_tree("test-tree")

    assert graph.tree.tree_key == "test-tree"
    assert graph.start_node.node_key == "start"
    assert graph.nodes_by_key["action"].action_payload == {"kind": "monitor"}
    assert graph.outgoing_edges_by_node_id[start_id][0].to_node_id == action_id
    assert graph.references_by_node_id[action_id][0].source_title == "Guideline"
    assert len(scripted_session.executed_statements) == 4


def test_coerce_node_type_rejects_unknown_type_with_typed_error() -> None:
    node = cast(
        DecisionNode,
        SimpleNamespace(node_key="mystery", node_type=SimpleNamespace(value="BOGUS")),
    )

    with pytest.raises(InvalidTreeStructure) as exc_info:
        _coerce_node_type(node, "test-tree")

    assert exc_info.value.tree_key == "test-tree"
    assert exc_info.value.node_key == "mystery"
    assert exc_info.value.details == {"reason": "unknown_node_type", "node_type": "BOGUS"}


def test_repository_tree_not_found_uses_one_query() -> None:
    scripted_session = ScriptedSession([StubResult(scalar=None)])
    repository = SqlAlchemyTreeGraphRepository(cast(Session, scripted_session))

    with pytest.raises(TreeNotFound) as exc_info:
        repository.get_tree("missing-tree")

    assert exc_info.value.tree_key == "missing-tree"
    assert len(scripted_session.executed_statements) == 1
