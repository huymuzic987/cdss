"""Stateless decision-tree evaluation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from cdss.api.dependencies import get_tree_graph_repository
from cdss.api.schemas import EvaluationErrorResponse, EvaluationRequest, EvaluationResponse
from cdss.core.config import Settings, get_settings
from cdss.domain.decision_tree import TreeGraphRepository, walk_tree

router = APIRouter(tags=["evaluation"])


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    responses={
        404: {"model": EvaluationErrorResponse},
        422: {"model": EvaluationErrorResponse},
        424: {"model": EvaluationErrorResponse},
        500: {"model": EvaluationErrorResponse},
    },
)
def evaluate(
    request: EvaluationRequest,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvaluationResponse:
    graph = repository.get_tree(request.start_tree_key)
    result = walk_tree(
        graph,
        request.input,
        max_steps=settings.cdss_max_steps,
        repository=repository,
    )
    return EvaluationResponse.from_result(result)
