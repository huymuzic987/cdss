"""Read/write access to a tree's saved editor-canvas layout.

Kept separate from ``SqlAlchemyTreeGraphRepository``/``CachingTreeGraphRepository``
on purpose: those treat a tree's structure (nodes/edges) as immutable and
optionally cache it process-wide, whereas a layout is mutable and written on
every canvas edit, so it must never share that cache.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from cdss.domain.decision_tree.errors import TreeNotFound
from cdss.infrastructure.db.models import DecisionTree, TreeLayout


class TreeLayoutRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_layout(self, tree_key: str) -> TreeLayout | None:
        """Return the saved layout for ``tree_key``, or ``None`` if none has been saved yet."""

        tree_id = self._resolve_tree_id(tree_key)
        return self._session.execute(
            select(TreeLayout).where(TreeLayout.tree_id == tree_id)
        ).scalar_one_or_none()

    def upsert_layout(
        self,
        tree_key: str,
        *,
        arrow_kind: str,
        node_positions: dict[str, Any],
        edge_layouts: dict[str, Any],
    ) -> TreeLayout:
        tree_id = self._resolve_tree_id(tree_key)
        layout = self._session.execute(
            select(TreeLayout).where(TreeLayout.tree_id == tree_id)
        ).scalar_one_or_none()
        if layout is None:
            layout = TreeLayout(tree_id=tree_id)
            self._session.add(layout)
        layout.arrow_kind = arrow_kind
        layout.node_positions = node_positions
        layout.edge_layouts = edge_layouts
        self._session.commit()
        self._session.refresh(layout)
        return layout

    def delete_layout(self, tree_key: str) -> None:
        tree_id = self._resolve_tree_id(tree_key)
        layout = self._session.execute(
            select(TreeLayout).where(TreeLayout.tree_id == tree_id)
        ).scalar_one_or_none()
        if layout is not None:
            self._session.delete(layout)
            self._session.commit()

    def _resolve_tree_id(self, tree_key: str):
        tree_id = self._session.execute(
            select(DecisionTree.id).where(DecisionTree.tree_key == tree_key)
        ).scalar_one_or_none()
        if tree_id is None:
            raise TreeNotFound(tree_key=tree_key)
        return tree_id
