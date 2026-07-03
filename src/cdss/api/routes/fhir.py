"""Read-only HL7 FHIR R4 export of the decision-tree knowledge base."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from cdss.api.dependencies import get_tree_graph_repository
from cdss.api.schemas import EvaluationErrorResponse
from cdss.api.schemas.fhir import Bundle, Library, PlanDefinition
from cdss.domain.decision_tree import TreeGraphRepository

router = APIRouter(prefix="/fhir", tags=["fhir"])


@router.get("/PlanDefinition", response_model=Bundle, response_model_exclude_none=True)
def list_plan_definitions(
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> Bundle:
    plan_definitions = [
        PlanDefinition.from_graph(repository.get_tree(tree.tree_key))
        for tree in repository.list_trees()
    ]
    return Bundle.from_plan_definitions(plan_definitions)


@router.get(
    "/PlanDefinition/{tree_key}",
    response_model=PlanDefinition,
    response_model_exclude_none=True,
    responses={404: {"model": EvaluationErrorResponse}},
)
def get_plan_definition(
    tree_key: str,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> PlanDefinition:
    graph = repository.get_tree(tree_key)
    return PlanDefinition.from_graph(graph)


@router.get(
    "/Library/{tree_key}",
    response_model=Library,
    response_model_exclude_none=True,
    responses={404: {"model": EvaluationErrorResponse}},
)
def get_library(
    tree_key: str,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
) -> Library:
    graph = repository.get_tree(tree_key)
    library = Library.from_graph(graph)
    if library is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"tree '{tree_key}' has no GLOBAL nodes",
        )
    return library
