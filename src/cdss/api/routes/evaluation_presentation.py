"""Shared response-shaping helpers for the /evaluate and /evaluate/follow-up routes."""

from cdss.api.routes.evaluation_medications import (
    enrich_inferred_medications as enrich_inferred_medications,
)
from cdss.api.routes.evaluation_pregnancy_presentation import enrich_pregnancy_action
from cdss.domain.decision_tree import (
    DecisionTreeError,
    ExecutedAction,
    FrozenJsonObject,
    JsonObject,
    NodeType,
    RunState,
    TraceEvent,
    TraversalResult,
    TreeGraphRepository,
    select_output_actions,
)

_PREGNANCY_TREE_KEY = "hypertension-in-pregnancy"
_PREGNANCY_MONITOR_NODE_KEY = "T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM"


def select_presentation_actions(
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
        if entry.event is TraceEvent.NODE_ENTERED and entry.tree_key == _PREGNANCY_TREE_KEY
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
            if action.tree_key == _PREGNANCY_TREE_KEY and action.node_key == terminal_entry.node_key
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
        enrich_pregnancy_action(action, result, graph)
        if action.tree_key == _PREGNANCY_TREE_KEY
        else action
        for action in exposed
    ]


def restore_raw_bundle(error: DecisionTreeError, bundle: JsonObject) -> None:
    """Keep the public error snapshot in the same canonical format as success."""

    state = error.partial_run_state
    if state is None:
        return
    error.partial_run_state = RunState(
        input_snapshot=FrozenJsonObject(bundle),
        context=state.context,
        actions=state.actions,
        trace=state.trace,
        references=state.references,
    )
