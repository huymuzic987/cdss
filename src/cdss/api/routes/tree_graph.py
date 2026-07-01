"""Read-only decision-tree structure endpoints for frontend visualization."""

from typing import Annotated

from fastapi import APIRouter, Depends

from cdss.api.dependencies import get_tree_graph_repository
from cdss.api.schemas import EvaluationErrorResponse, TreeGraphResponse, TreeSummary
from cdss.domain.decision_tree import TreeGraphRepository

router = APIRouter(tags=["tree-graph"])


@router.get("/trees", response_model=list[TreeSummary])
def list_trees(
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> list[TreeSummary]:
    return [
        TreeSummary(tree_key=tree.tree_key, name_en=tree.name_en, name_vi=tree.name_vi)
        for tree in repository.list_trees()
    ]


@router.get(
    "/trees/{tree_key}/graph",
    response_model=TreeGraphResponse,
    responses={404: {"model": EvaluationErrorResponse}},
)
def get_tree_graph(
    tree_key: str,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> TreeGraphResponse:
    graph = repository.get_tree(tree_key)
    return TreeGraphResponse.from_graph(graph)
