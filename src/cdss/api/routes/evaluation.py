"""Stateless decision-tree evaluation of one canonical clinical FHIR Bundle."""

from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Depends

from cdss.api.dependencies import get_medicine_repository, get_tree_graph_repository
from cdss.api.schemas import EvaluationErrorResponse, EvaluationResponse
from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.api.schemas.clinical_presentation import attach_terminal_presentation
from cdss.core.config import Settings, get_settings
from cdss.domain.decision_tree import (
    DecisionTreeError,
    ExecutedAction,
    InvalidFhirInput,
    JsonObject,
    MedicineRepository,
    NodeType,
    RunState,
    TraceEvent,
    TraversalResult,
    TreeGraph,
    TreeGraphRepository,
    select_output_actions,
    walk_tree,
)
from cdss.domain.follow_up import (
    FollowUpType,
    build_current_visit_input,
    build_previous_visit_input,
    has_complete_previous_bp,
    infer_follow_up,
)

router = APIRouter(tags=["evaluation"])

_MEDICATION_FOLLOW_UP_TREE_KEY = "treatment-threshold-and-bp-target"
_INITIAL_VISIT_TREE_KEY = "hypertension-diagnosis"
_PREGNANCY_TREE_KEY = "hypertension-in-pregnancy"
_PREGNANCY_MONITOR_NODE_KEY = "T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM"


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
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvaluationResponse:
    parsed = parse_clinical_bundle(bundle)
    runtime_input = parsed.runtime_input
    inference = None
    start_tree_key = _INITIAL_VISIT_TREE_KEY

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
            _restore_raw_bundle(error, parsed.raw_bundle)
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
        if inference.follow_up_type != FollowUpType.INITIAL_VISIT:
            start_tree_key = _MEDICATION_FOLLOW_UP_TREE_KEY

    try:
        result = walk_tree(
            repository.get_tree(start_tree_key),
            runtime_input,
            max_steps=settings.cdss_max_steps,
            repository=repository,
            medicine_repository=medicine_repository,
        )
    except DecisionTreeError as error:
        _restore_raw_bundle(error, parsed.raw_bundle)
        raise
    selected_actions = _select_presentation_actions(
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
        inferred_follow_up_type=inference.follow_up_type if inference else None,
        previous_recommended_action_types=(
            list(inference.previous_action_types) if inference else None
        ),
    )


def _select_presentation_actions(
    result: TraversalResult,
    repository: TreeGraphRepository,
    *,
    debug_output: bool,
) -> list[ExecutedAction]:
    """Keep pregnancy's monitor checkpoint as well as its terminal recommendation."""

    selected = select_output_actions(result.actions, debug_output=debug_output)
    pregnancy_entries = [
        entry
        for entry in result.trace
        if entry.event is TraceEvent.NODE_ENTERED
        and entry.tree_key == _PREGNANCY_TREE_KEY
    ]
    if not pregnancy_entries:
        return selected

    graph = repository.get_tree(_PREGNANCY_TREE_KEY)
    monitor = next(
        (
            action
            for action in result.actions
            if action.tree_key == _PREGNANCY_TREE_KEY
            and action.node_key == _PREGNANCY_MONITOR_NODE_KEY
        ),
        None,
    )
    terminal_entry = pregnancy_entries[-1]
    terminal = next(
        (
            action
            for action in reversed(result.actions)
            if action.tree_key == _PREGNANCY_TREE_KEY
            and action.node_key == terminal_entry.node_key
        ),
        None,
    )
    if terminal is None:
        terminal_node = graph.nodes_by_key[terminal_entry.node_key]
        if terminal_node.node_type is NodeType.END:
            terminal = ExecutedAction(
                tree_key=_PREGNANCY_TREE_KEY,
                node_key=terminal_node.node_key,
                node_type=terminal_node.node_type,
                text_en=terminal_node.text_en,
                text_vi=terminal_node.text_vi,
                payload={},
            )

    pregnancy_actions = [action for action in (monitor, terminal) if action is not None]
    if debug_output:
        exposed = list(selected)
        existing = {(action.tree_key, action.node_key) for action in exposed}
        exposed.extend(
            action
            for action in pregnancy_actions
            if (action.tree_key, action.node_key) not in existing
        )
    else:
        exposed = pregnancy_actions or selected

    return [
        _enrich_pregnancy_action(action, result, graph)
        if action.tree_key == _PREGNANCY_TREE_KEY
        else action
        for action in exposed
    ]


def _enrich_pregnancy_action(
    action: ExecutedAction,
    result: TraversalResult,
    graph: TreeGraph,
) -> ExecutedAction:
    enriched = action.model_copy(deep=True)
    cutoff = next(
        (
            index
            for index, entry in enumerate(result.trace)
            if entry.event is TraceEvent.NODE_ENTERED
            and entry.tree_key == action.tree_key
            and entry.node_key == action.node_key
        ),
        len(result.trace) - 1,
    )
    seen: set[str] = set()
    regimen_summary: list[JsonObject] = []
    for entry in result.trace[: cutoff + 1]:
        if (
            entry.event is not TraceEvent.NODE_ENTERED
            or entry.tree_key != _PREGNANCY_TREE_KEY
            or entry.node_type is not NodeType.INFERENCE
            or entry.node_key in seen
        ):
            continue
        seen.add(entry.node_key)
        node = graph.nodes_by_key[entry.node_key]
        regimen_summary.append(
            {
                "id": entry.node_key,
                "text_en": node.text_en,
                "text_vi": node.text_vi,
            }
        )
    if regimen_summary:
        enriched.payload["regimen_summary"] = regimen_summary

    safety_notes = _pregnancy_safety_notes(graph.global_nodes)
    if safety_notes:
        enriched.payload["safety_notes"] = safety_notes
    enriched.text_en = _pregnancy_recommendation_text(
        action.text_en,
        regimen_summary,
        safety_notes,
        locale="en",
    )
    enriched.text_vi = _pregnancy_recommendation_text(
        action.text_vi,
        regimen_summary,
        safety_notes,
        locale="vi",
    )
    _append_pregnancy_safety_actions(enriched, safety_notes)
    return enriched


def _pregnancy_recommendation_text(
    recommendation: str,
    regimen_summary: list[JsonObject],
    safety_notes: list[JsonObject],
    *,
    locale: str,
) -> str:
    regimen_heading = "Recorded regimen" if locale == "en" else "Phác đồ đã ghi nhận"
    safety_heading = "Pregnancy safety" if locale == "en" else "An toàn thai kỳ"
    text_key = "text_en" if locale == "en" else "text_vi"
    sections = [recommendation]
    regimen_lines = [
        item[text_key]
        for item in regimen_summary
        if isinstance(item.get(text_key), str)
    ]
    safety_lines = [
        item[text_key]
        for item in safety_notes
        if isinstance(item.get(text_key), str)
    ]
    if regimen_lines:
        sections.append(f"{regimen_heading}:\n- " + "\n- ".join(regimen_lines))
    if safety_lines:
        sections.append(f"{safety_heading}:\n- " + "\n- ".join(safety_lines))
    return "\n\n".join(sections)


def _append_pregnancy_safety_actions(
    action: ExecutedAction,
    safety_notes: list[JsonObject],
) -> None:
    existing = action.payload.get("additional_actions")
    additional_actions = list(existing) if isinstance(existing, list) else []
    for note in safety_notes:
        additional_actions.append(
            {
                "id": f"pregnancy-safety-{note['id']}",
                "label_en": note["text_en"],
                "label_vi": note["text_vi"],
            }
        )
    if additional_actions:
        action.payload["additional_actions"] = additional_actions


def _pregnancy_safety_notes(global_nodes) -> list[JsonObject]:
    notes: list[JsonObject] = []
    for node in global_nodes:
        config = node.global_config
        if not isinstance(config, Mapping) or config.get("kind") != "OVERRIDE_NOTE":
            continue
        details = config.get("details")
        if not isinstance(details, Mapping):
            continue
        for key, raw_detail in details.items():
            if not isinstance(raw_detail, Mapping):
                continue
            label_en = raw_detail.get("label_en") or raw_detail.get("label")
            label_vi = raw_detail.get("label_vi") or raw_detail.get("label") or label_en
            items_en = raw_detail.get("items_en") or raw_detail.get("items") or []
            items_vi = raw_detail.get("items_vi") or raw_detail.get("items") or items_en
            en = _join_note(label_en, items_en)
            vi = _join_note(label_vi, items_vi)
            if en or vi:
                notes.append(
                    {
                        "id": str(key),
                        "text_en": en or vi,
                        "text_vi": vi or en,
                    }
                )
    return notes


def _join_note(label, items) -> str:
    prefix = label if isinstance(label, str) else ""
    values = (
        [item for item in items if isinstance(item, str)]
        if isinstance(items, (list, tuple))
        else []
    )
    if prefix and values:
        return f"{prefix}: {', '.join(values)}"
    return prefix or ", ".join(values)


def _restore_raw_bundle(error: DecisionTreeError, bundle: JsonObject) -> None:
    """Keep the public error snapshot in the same canonical format as success."""

    state = error.partial_run_state
    if state is None:
        return
    error.partial_run_state = RunState(
        input_snapshot=bundle,
        context=state.context,
        actions=state.actions,
        trace=state.trace,
        references=state.references,
    )
