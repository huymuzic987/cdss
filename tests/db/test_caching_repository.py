"""Behavioral tests for the opt-in graph caching layer."""

from __future__ import annotations

from typing import cast

import pytest

from cdss.domain.decision_tree import TreeNotFound
from cdss.domain.decision_tree.graph import TreeDefinition, TreeGraph
from cdss.infrastructure.db.caching_repository import (
    CachingTreeGraphRepository,
    TreeGraphCache,
)


class CountingRepository:
    """Repository stub that records every load and can fail on demand."""

    def __init__(self, graphs: dict[str, object]) -> None:
        self._graphs = graphs
        self.calls: list[str] = []

    def get_tree(self, tree_key: str) -> TreeGraph:
        self.calls.append(tree_key)
        if tree_key not in self._graphs:
            raise TreeNotFound(tree_key=tree_key)
        return cast(TreeGraph, self._graphs[tree_key])

    def list_trees(self) -> list[TreeDefinition]:
        return [cast(TreeGraph, graph).tree for graph in self._graphs.values()]


def test_cache_loads_each_tree_once_across_repository_instances() -> None:
    cache = TreeGraphCache()
    graph = object()

    first = CountingRepository({"tree-a": graph})
    assert CachingTreeGraphRepository(first, cache).get_tree("tree-a") is graph

    # A later request builds a fresh inner repository (new session) but shares
    # the process cache: no second DB load.
    second = CountingRepository({"tree-a": object()})
    assert CachingTreeGraphRepository(second, cache).get_tree("tree-a") is graph

    assert first.calls == ["tree-a"]
    assert second.calls == []


def test_cache_does_not_store_failed_loads() -> None:
    cache = TreeGraphCache()
    inner = CountingRepository({})
    repository = CachingTreeGraphRepository(inner, cache)

    with pytest.raises(TreeNotFound):
        repository.get_tree("later-seeded")

    # The tree appears after a re-seed; the next call must reach the inner repo.
    graph = object()
    inner._graphs["later-seeded"] = graph
    assert repository.get_tree("later-seeded") is graph
    assert inner.calls == ["later-seeded", "later-seeded"]


def test_clear_forces_reload() -> None:
    cache = TreeGraphCache()
    inner = CountingRepository({"tree-a": object()})
    repository = CachingTreeGraphRepository(inner, cache)

    repository.get_tree("tree-a")
    cache.clear()
    repository.get_tree("tree-a")

    assert inner.calls == ["tree-a", "tree-a"]
