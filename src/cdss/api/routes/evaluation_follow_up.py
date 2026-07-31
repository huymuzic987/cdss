"""Medication follow-up evaluation with an already-known stage and BP target."""

from typing import Annotated

from fastapi import APIRouter, Depends

from cdss.api.dependencies import get_medicine_repository, get_tree_graph_repository
from cdss.api.routes.evaluation_presentation import (
    enrich_inferred_medications,
    restore_raw_bundle,
    select_presentation_actions,
)
from cdss.api.schemas import EvaluationErrorResponse, EvaluationResponse
from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.api.schemas.clinical_presentation import attach_terminal_presentation
from cdss.core.config import Settings, get_settings
from cdss.domain.decision_tree import (
    DecisionTreeError,
    InvalidFhirInput,
    JsonObject,
    MedicineRepository,
    TreeGraphRepository,
    walk_tree,
)

router = APIRouter(tags=["evaluation"])

_MEDICATION_FOLLOW_UP_TREE_KEY = "treatment-threshold-and-bp-target"


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
    bundle: JsonObject,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
    medicine_repository: Annotated[MedicineRepository, Depends(get_medicine_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvaluationResponse:
    """Evaluate a medication follow-up whose stage and BP target are already known.

    Skips the previous-visit replay/inference `/evaluate` relies on - that
    replay always walks a brand-new-diagnosis path and can therefore only ever
    conclude ``INITIAL_REGIMEN``, never ``ESCALATED_REGIMEN``. Callers who
    already know the patient is on an escalated regimen (e.g. an EHR with real
    visit history) use this endpoint instead.
    """

    parsed = parse_clinical_bundle(bundle)
    runtime_input = dict(parsed.runtime_input)

    stage = runtime_input.get("medication_follow_up_stage")
    sbp_upper = runtime_input.pop("active_bp_target_sbp_upper", None)
    dbp_upper = runtime_input.pop("active_bp_target_dbp_upper", None)
    missing = [
        name
        for name, value in (
            ("medication_follow_up_stage", stage),
            ("active_bp_target_sbp_upper", sbp_upper),
            ("active_bp_target_dbp_upper", dbp_upper),
            ("current_clinic_sbp", runtime_input.get("current_clinic_sbp")),
            ("current_clinic_dbp", runtime_input.get("current_clinic_dbp")),
        )
        if value is None
    ]
    if missing:
        raise InvalidFhirInput(
            details={"reason": f"missing required field(s): {', '.join(missing)}"}
        )

    runtime_input["is_medication_follow_up"] = True
    runtime_input["is_lifestyle_follow_up"] = False
    runtime_input["active_bp_target"] = {
        "sbp": {"upper_exclusive_mmhg": sbp_upper},
        "dbp": {"upper_exclusive_mmhg": dbp_upper},
    }

    try:
        result = walk_tree(
            repository.get_tree(_MEDICATION_FOLLOW_UP_TREE_KEY),
            runtime_input,
            max_steps=settings.cdss_max_steps,
            repository=repository,
            medicine_repository=medicine_repository,
        )
    except DecisionTreeError as error:
        restore_raw_bundle(error, parsed.raw_bundle)
        raise
    selected_actions = select_presentation_actions(
        result,
        repository,
        debug_output=settings.debug_output,
    )
    selected_actions = enrich_inferred_medications(
        selected_actions, result, repository, medicine_repository
    )
    presented_actions = [
        presented
        for action in selected_actions
        for presented in attach_terminal_presentation(
            [action],
            parsed,
            result.references,
        )
    ]
    return EvaluationResponse.from_result(
        result,
        debug_output=settings.debug_output,
        input_snapshot=parsed.raw_bundle,
        actions=presented_actions,
    )
