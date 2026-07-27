"""Schemas for the saved editor-canvas layout of a tree (node positions, connector style)."""

from __future__ import annotations

from typing import Any, Literal, cast

from cdss.api.schemas.evaluation import ApiModel
from cdss.infrastructure.db.models import TreeLayout


class NodePosition(ApiModel):
    x: float
    y: float


class TreeLayoutResponse(ApiModel):
    positions: dict[str, NodePosition]
    arrow_kind: Literal["straight", "elbow"]
    edge_layouts: dict[str, dict[str, Any]]

    @classmethod
    def from_model(cls, layout: TreeLayout | None) -> TreeLayoutResponse:
        if layout is None:
            return cls(positions={}, arrow_kind="elbow", edge_layouts={})
        return cls(
            positions={
                node_key: NodePosition(x=position["x"], y=position["y"])
                for node_key, position in layout.node_positions.items()
            },
            arrow_kind=cast('Literal["straight", "elbow"]', layout.arrow_kind),
            edge_layouts=layout.edge_layouts,
        )


class TreeLayoutRequest(ApiModel):
    positions: dict[str, NodePosition]
    arrow_kind: Literal["straight", "elbow"]
    edge_layouts: dict[str, dict[str, Any]] = {}
