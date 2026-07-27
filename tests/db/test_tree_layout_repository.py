"""Database-free tests for the tree layout repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from cdss.domain.decision_tree import TreeNotFound
from cdss.infrastructure.db.models import TreeLayout
from cdss.infrastructure.db.tree_layout_repository import TreeLayoutRepository


class StubResult:
    def __init__(self, *, scalar: Any = None) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class ScriptedSession:
    def __init__(self, results: Sequence[StubResult]) -> None:
        self._results = iter(results)
        self.executed_statements: list[Executable] = []
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self.commit_count = 0
        self.refreshed: list[Any] = []

    def execute(self, statement: Executable) -> StubResult:
        self.executed_statements.append(statement)
        return next(self._results)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def delete(self, obj: Any) -> None:
        self.deleted.append(obj)

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, obj: Any) -> None:
        self.refreshed.append(obj)


TREE_ID = UUID(int=1)


def test_get_layout_returns_none_when_none_saved() -> None:
    scripted_session = ScriptedSession([StubResult(scalar=TREE_ID), StubResult(scalar=None)])
    repository = TreeLayoutRepository(cast(Session, scripted_session))

    assert repository.get_layout("test-tree") is None
    assert len(scripted_session.executed_statements) == 2


def test_get_layout_raises_tree_not_found_for_unknown_tree_key() -> None:
    scripted_session = ScriptedSession([StubResult(scalar=None)])
    repository = TreeLayoutRepository(cast(Session, scripted_session))

    with pytest.raises(TreeNotFound) as exc_info:
        repository.get_layout("missing-tree")

    assert exc_info.value.tree_key == "missing-tree"
    assert len(scripted_session.executed_statements) == 1


def test_upsert_layout_creates_row_when_none_exists() -> None:
    scripted_session = ScriptedSession([StubResult(scalar=TREE_ID), StubResult(scalar=None)])
    repository = TreeLayoutRepository(cast(Session, scripted_session))

    layout = repository.upsert_layout(
        "test-tree",
        arrow_kind="straight",
        node_positions={"n1": {"x": 1.0, "y": 2.0}},
        edge_layouts={"n1->n2": {"bend": 4}},
    )

    assert layout.tree_id == TREE_ID
    assert layout.arrow_kind == "straight"
    assert layout.node_positions == {"n1": {"x": 1.0, "y": 2.0}}
    assert layout.edge_layouts == {"n1->n2": {"bend": 4}}
    assert scripted_session.added == [layout]
    assert scripted_session.commit_count == 1
    assert scripted_session.refreshed == [layout]


def test_upsert_layout_updates_existing_row_in_place() -> None:
    existing = TreeLayout(tree_id=TREE_ID, arrow_kind="elbow", node_positions={})
    scripted_session = ScriptedSession([StubResult(scalar=TREE_ID), StubResult(scalar=existing)])
    repository = TreeLayoutRepository(cast(Session, scripted_session))

    layout = repository.upsert_layout(
        "test-tree",
        arrow_kind="straight",
        node_positions={"n1": {"x": 5.0, "y": 6.0}},
        edge_layouts={},
    )

    assert layout is existing
    assert layout.arrow_kind == "straight"
    assert scripted_session.added == []
    assert scripted_session.commit_count == 1


def test_delete_layout_deletes_existing_row() -> None:
    existing = TreeLayout(tree_id=TREE_ID, arrow_kind="elbow", node_positions={})
    scripted_session = ScriptedSession([StubResult(scalar=TREE_ID), StubResult(scalar=existing)])
    repository = TreeLayoutRepository(cast(Session, scripted_session))

    repository.delete_layout("test-tree")

    assert scripted_session.deleted == [existing]
    assert scripted_session.commit_count == 1


def test_delete_layout_is_a_no_op_when_nothing_saved() -> None:
    scripted_session = ScriptedSession([StubResult(scalar=TREE_ID), StubResult(scalar=None)])
    repository = TreeLayoutRepository(cast(Session, scripted_session))

    repository.delete_layout("test-tree")

    assert scripted_session.deleted == []
    assert scripted_session.commit_count == 0
