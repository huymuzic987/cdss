"""Persisted editor-canvas layout for a tree (node positions, connector style).

Replaces the tldraw canvas's previous browser-localStorage persistence so a
layout is shared across users/machines instead of per-browser.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from cdss.api.dependencies import get_tree_layout_repository
from cdss.api.schemas import EvaluationErrorResponse, TreeLayoutRequest, TreeLayoutResponse
from cdss.infrastructure.db.tree_layout_repository import TreeLayoutRepository

router = APIRouter(tags=["tree-layout"])


@router.get(
    "/trees/{tree_key}/layout",
    response_model=TreeLayoutResponse,
    responses={404: {"model": EvaluationErrorResponse}},
)
def get_tree_layout(
    tree_key: str,
    repository: Annotated[TreeLayoutRepository, Depends(get_tree_layout_repository)],
) -> TreeLayoutResponse:
    return TreeLayoutResponse.from_model(repository.get_layout(tree_key))


@router.put(
    "/trees/{tree_key}/layout",
    response_model=TreeLayoutResponse,
    responses={404: {"model": EvaluationErrorResponse}},
)
def put_tree_layout(
    tree_key: str,
    body: TreeLayoutRequest,
    repository: Annotated[TreeLayoutRepository, Depends(get_tree_layout_repository)],
) -> TreeLayoutResponse:
    layout = repository.upsert_layout(
        tree_key,
        arrow_kind=body.arrow_kind,
        node_positions={key: position.model_dump() for key, position in body.positions.items()},
    )
    return TreeLayoutResponse.from_model(layout)


@router.delete(
    "/trees/{tree_key}/layout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": EvaluationErrorResponse}},
)
def delete_tree_layout(
    tree_key: str,
    repository: Annotated[TreeLayoutRepository, Depends(get_tree_layout_repository)],
) -> None:
    repository.delete_layout(tree_key)
