"""Optional process-level caching layer for immutable tree graphs.

Decision-tree graphs are immutable frozen dataclasses detached from any ORM
session, so a loaded graph can be safely reused across requests. The only cost
is staleness: if a tree is re-seeded, a cached graph keeps serving the previous
definition until the cache is cleared. Because a stale clinical tree is a
correctness risk, this layer is **opt-in** (``CDSS_GRAPH_CACHE_ENABLED``) and
defaults to off. When enabled, a deployment owns invalidation via
``TreeGraphCache.clear()`` after any re-seed.

Within a single traversal each tree is already loaded at most once (cross-tree
links cannot re-enter a visited tree), so this cache only removes *cross-request*
reloads; it changes no single-run behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from cdss.domain.decision_tree.graph import TreeGraph, TreeGraphRepository


class TreeGraphCache:
    """Process-lifetime store of successfully loaded, immutable tree graphs."""

    def __init__(self) -> None:
        self._store: dict[str, TreeGraph] = {}

    def get_or_load(self, tree_key: str, loader: Callable[[], TreeGraph]) -> TreeGraph:
        cached = self._store.get(tree_key)
        if cached is not None:
            return cached
        # Load outside any lock: the loader may raise (e.g. TreeNotFound), which
        # must propagate and must not be cached so a later seed is picked up.
        graph = loader()
        self._store[tree_key] = graph
        return graph

    def clear(self) -> None:
        self._store.clear()


class CachingTreeGraphRepository(TreeGraphRepository):
    """Wrap a repository, serving immutable graphs from a shared cache."""

    def __init__(self, inner: TreeGraphRepository, cache: TreeGraphCache) -> None:
        self._inner = inner
        self._cache = cache

    def get_tree(self, tree_key: str) -> TreeGraph:
        return self._cache.get_or_load(tree_key, lambda: self._inner.get_tree(tree_key))


@lru_cache(maxsize=1)
def get_graph_cache() -> TreeGraphCache:
    """Return the process-wide graph cache (one instance per process)."""

    return TreeGraphCache()
