"""Stateless decision-tree evaluation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from cdss.api.dependencies import get_tree_graph_repository
from cdss.api.schemas import (
    EvaluationErrorResponse,
    EvaluationRequest,
    EvaluationResponse,
    FollowUpEvaluationRequest,
    FollowUpEvaluationResponse,
)
from cdss.core.config import Settings, get_settings
from cdss.domain.decision_tree import MissingRuntimePath, TreeGraphRepository, walk_tree

router = APIRouter(tags=["evaluation"])

# The diagnosis tree that re-derives a patient's active BP target from
# diagnosis-time facts (age, comorbidities, the clinic readings that
# established the hypertension grade), and the two treatment trees a
# follow-up comparison is run against depending on facility resources.
_DIAGNOSIS_TREE_KEY = "hypertension-diagnosis"
_FACILITY_TREATMENT_TREE_KEYS = {
    "LIMITED_RESOURCES": "essential-treatment-strategy",
    "FULL_RESOURCES": "optimal-treatment-strategy",
}


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


@router.post(
    "/evaluate/follow-up",
    response_model=FollowUpEvaluationResponse,
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
    settings: Annotated[Settings, Depends(get_settings)],
) -> FollowUpEvaluationResponse:
    """Re-derive a patient's active BP target from diagnosis-time facts, then
    compare it against today's follow-up reading. Neither call persists
    anything; the target is recomputed fresh from the same facts every time
    instead of being trusted as caller-supplied state.
    """
    derivation_graph = repository.get_tree(_DIAGNOSIS_TREE_KEY)
    derivation = walk_tree(
        derivation_graph,
        {
            **request.diagnosis_input,
            "is_medication_follow_up": False,
            "facility_capability": request.facility_capability,
        },
        max_steps=settings.cdss_max_steps,
        repository=repository,
    )

    treatment_context = derivation.context.get("treatment")
    bp_target = treatment_context.get("bp_target") if isinstance(treatment_context, dict) else None
    if not isinstance(bp_target, dict):
        raise MissingRuntimePath(
            message=(
                "Derivation traversal completed without producing "
                "context.treatment.bp_target; the diagnosis input may not "
                "represent a hypertensive patient."
            ),
            tree_key=_DIAGNOSIS_TREE_KEY,
            details={"reason": "bp_target_not_derived", "path": "context.treatment.bp_target"},
        )

    comparison_tree_key = _FACILITY_TREATMENT_TREE_KEYS.get(request.facility_capability)
    if comparison_tree_key is None:
        raise MissingRuntimePath(
            message=(
                f"Unknown facility_capability '{request.facility_capability}'; "
                f"expected one of {sorted(_FACILITY_TREATMENT_TREE_KEYS)}."
            ),
            details={"reason": "unknown_facility_capability"},
        )

    comparison_graph = repository.get_tree(comparison_tree_key)
    comparison = walk_tree(
        comparison_graph,
        {
            "is_medication_follow_up": True,
            "medication_follow_up_stage": request.medication_follow_up_stage,
            "active_bp_target": bp_target,
            "current_clinic_sbp": request.current_clinic_sbp,
            "current_clinic_dbp": request.current_clinic_dbp,
            "facility_capability": request.facility_capability,
        },
        max_steps=settings.cdss_max_steps,
        repository=repository,
    )

    return FollowUpEvaluationResponse.from_results(
        active_bp_target=bp_target,
        derivation=derivation,
        comparison=comparison,
    )
