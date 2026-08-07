"""Stateless decision-tree evaluation of one canonical clinical FHIR Bundle."""

from typing import Annotated

from fastapi import APIRouter, Depends

from cdss.api.dependencies import (
    get_contraindication_repository,
    get_medicine_repository,
    get_tree_graph_repository,
)
from cdss.api.routes import evaluation_follow_up
from cdss.api.routes.evaluation_presentation import (
    enrich_inferred_medications,
    restore_raw_bundle,
    select_presentation_actions,
)
from cdss.api.schemas import EvaluationErrorResponse, EvaluationResponse
from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.api.schemas.clinical_presentation import attach_terminal_presentation
from cdss.core.config import Settings, get_settings
from cdss.domain.contraindications.contraindication_catalog import ContraindicationDrugRepository
from cdss.domain.contraindications.contraindication_evaluator import prepare_contraindication_input
from cdss.domain.decision_tree import (
    DecisionTreeError,
    ExecutedAction,
    InvalidFhirInput,
    JsonObject,
    MedicineRepository,
    TreeGraphRepository,
    walk_tree,
)
from cdss.domain.follow_up import (
    FollowUpType,
    build_current_visit_input,
    build_previous_visit_input,
    has_complete_previous_bp,
    infer_follow_up,
)
from cdss.domain.follow_up.pregnancy_follow_up import (
    PREGNANCY_TREE_KEY,
    pregnancy_follow_up_entry_node,
    summarize_pregnancy_follow_up,
)

router = APIRouter(tags=["evaluation"])
router.include_router(evaluation_follow_up.router)

_MEDICATION_FOLLOW_UP_TREE_KEY = "treatment-threshold-and-bp-target"
_INITIAL_VISIT_TREE_KEY = "hypertension-diagnosis"


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
    bundle: JsonObject,
    repository: Annotated[TreeGraphRepository, Depends(get_tree_graph_repository)],
    medicine_repository: Annotated[MedicineRepository, Depends(get_medicine_repository)],
    contraindication_repository: Annotated[
        ContraindicationDrugRepository, Depends(get_contraindication_repository)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvaluationResponse:
    parsed = parse_clinical_bundle(bundle)
    runtime_input = prepare_contraindication_input(
        parsed.runtime_input,
        parsed.raw_bundle,
        contraindication_repository,
    )
    inference = None
    start_tree_key = _INITIAL_VISIT_TREE_KEY
    start_node_key = None

    if has_complete_previous_bp(runtime_input):
        try:
            previous_result = walk_tree(
                repository.get_tree(_INITIAL_VISIT_TREE_KEY),
                build_previous_visit_input(runtime_input),
                max_steps=settings.cdss_max_steps,
                repository=repository,
                medicine_repository=medicine_repository,
            )
        except DecisionTreeError as error:
            restore_raw_bundle(error, parsed.raw_bundle)
            raise
        inference = infer_follow_up(previous_result)
        if (
            inference.follow_up_type == FollowUpType.MEDICATION_FOLLOW_UP
            and inference.active_bp_target is None
        ):
            raise InvalidFhirInput(
                details={
                    "reason": "Previous medication recommendation did not establish a BP target"
                }
            )
        runtime_input = build_current_visit_input(runtime_input, inference)
        if inference.follow_up_type in {
            FollowUpType.LIFESTYLE_FOLLOW_UP,
            FollowUpType.MEDICATION_FOLLOW_UP,
        }:
            start_tree_key = _MEDICATION_FOLLOW_UP_TREE_KEY
        elif inference.follow_up_type == FollowUpType.PREGNANCY_FOLLOW_UP:
            start_tree_key = PREGNANCY_TREE_KEY
            start_node_key = pregnancy_follow_up_entry_node(runtime_input)

    try:
        result = walk_tree(
            repository.get_tree(start_tree_key),
            runtime_input,
            start_node_key=start_node_key,
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
    if not selected_actions:
        entered = next(
            (entry for entry in reversed(result.trace) if entry.event.value == "node_entered"),
            None,
        )
        if entered is not None:
            graph = repository.get_tree(entered.tree_key)
            node = graph.nodes_by_key[entered.node_key]
            selected_actions = [
                ExecutedAction(
                    tree_key=entered.tree_key,
                    node_key=entered.node_key,
                    node_type=entered.node_type,
                    text_en=node.text_en,
                    text_vi=node.text_vi,
                    payload={},
                )
            ]
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
    pregnancy_follow_up = summarize_pregnancy_follow_up(
        runtime_input,
        patient_id=parsed.patient_id,
        encounter_ids=parsed.encounter_ids,
        encounter_dates=parsed.encounter_dates,
        actions=result.actions,
    )
    return EvaluationResponse.from_result(
        result,
        debug_output=settings.debug_output,
        input_snapshot=parsed.raw_bundle,
        actions=presented_actions,
        inferred_follow_up_type=inference.follow_up_type if inference else None,
        previous_recommended_action_types=(
            list(inference.previous_action_types) if inference else None
        ),
        pregnancy_follow_up=pregnancy_follow_up,
    )
