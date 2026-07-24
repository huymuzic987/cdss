"""Stateless decision-tree evaluation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from cdss.api.dependencies import get_medicine_repository, get_tree_graph_repository
from cdss.api.schemas import (
    EvaluationErrorResponse,
    EvaluationRequest,
    EvaluationResponse,
    FollowUpEvaluationRequest,
)
from cdss.core.config import Settings, get_settings
from cdss.domain.decision_tree import (
    MedicineRepository,
    MissingRuntimePath,
    TreeGraphRepository,
    walk_tree,
)

router = APIRouter(tags=["evaluation"])

# Tree 3 owns follow-up routing: given an already-known active_bp_target, it
# restores that target into context and links onward to the facility's
# treatment-strategy tree (essential or optimal) based on input.facility_capability.
_MEDICATION_FOLLOW_UP_TREE_KEY = "treatment-threshold-and-bp-target"


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
    medicine_repository: Annotated[MedicineRepository, Depends(get_medicine_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvaluationResponse:
    graph = repository.get_tree(request.start_tree_key)
    result = walk_tree(
        graph,
        request.input,
        max_steps=settings.cdss_max_steps,
        repository=repository,
        medicine_repository=medicine_repository,
    )
    return EvaluationResponse.from_result(result)


@router.post(
    "/evaluate/follow-up",
    response_model=EvaluationResponse,
    responses={
        404: {"model": EvaluationErrorResponse},
        422: {"model": EvaluationErrorResponse},
        424: {"model": EvaluationErrorResponse},
        500: {"model": EvaluationErrorResponse},
    },
)
def evaluate_follow_up(
    request: FollowUpEvaluationRequest,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
    medicine_repository: Annotated[MedicineRepository, Depends(get_medicine_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvaluationResponse:
    """Compare today's follow-up reading against an already-known active BP
    target. The target is caller-supplied (it was established at diagnosis
    or the last lifestyle/medication follow-up) — this endpoint does not
    re-derive it, it just restores it into context via Tree 3 and lets Tree 3
    route to the facility's treatment-strategy tree.
    """
    graph = repository.get_tree(_MEDICATION_FOLLOW_UP_TREE_KEY)
    result = walk_tree(
        graph,
        {
            "is_medication_follow_up": True,
            "medication_follow_up_stage": request.medication_follow_up_stage,
            "active_bp_target": request.active_bp_target,
            "current_clinic_sbp": request.current_clinic_sbp,
            "current_clinic_dbp": request.current_clinic_dbp,
            "facility_capability": request.facility_capability,
        },
        max_steps=settings.cdss_max_steps,
        repository=repository,
        medicine_repository=medicine_repository,
    )
    return EvaluationResponse.from_result(result)
