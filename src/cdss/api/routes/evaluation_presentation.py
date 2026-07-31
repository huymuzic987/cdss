"""Shared response-shaping helpers for the /evaluate and /evaluate/follow-up routes."""

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
from cdss.domain.decision_tree.drug_classes import build_medicine_options
from cdss.domain.decision_tree.medicine_catalog import MedicineRepository

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


def enrich_inferred_medications(
    actions: list[ExecutedAction],
    result: TraversalResult,
    repository: TreeGraphRepository,
    medicine_repository: MedicineRepository,
) -> list[ExecutedAction]:
    """Resolve regimens established by entered inference nodes into catalog drugs."""

    inferred_names: set[str] = set()
    catalog = list(medicine_repository.list_all())
    for entry in result.trace:
        if entry.event is not TraceEvent.NODE_ENTERED or entry.node_type is not NodeType.INFERENCE:
            continue
        node = repository.get_tree(entry.tree_key).nodes_by_key[entry.node_key]
        text = f"{node.text_en} {node.text_vi}".casefold()
        for medicine in catalog:
            if medicine.name.casefold() not in text or _negated_medication(medicine.name, text):
                continue
            inferred_names.add(medicine.drug_id)

    options = build_medicine_options(result.context, medicine_repository)
    output: list[ExecutedAction] = []
    for action in actions:
        payload = dict(action.payload)
        if options and "medicine_options" not in payload:
            payload["medicine_options"] = options
        if inferred_names and "medicines" not in payload:
            payload["medicines"] = [
                {
                    "drug_id": medicine.drug_id,
                    "name": medicine.name,
                    "drug_class": medicine.drug_class,
                    "subgroup": medicine.subgroup,
                    "route": medicine.route,
                    "dose_low": medicine.dose_low,
                    "dose_usual": medicine.dose_usual,
                    "dose_max": medicine.dose_max,
                    "source": medicine.source,
                    "link": medicine.link,
                    "available": medicine.available,
                }
                for medicine in catalog
                if medicine.drug_id in inferred_names
            ]
        output.append(action.model_copy(update={"payload": payload}))
    return output


def _negated_medication(name: str, text: str) -> bool:
    """Do not turn contraindication/safety prose into a recommended medicine."""
    lowered = text.casefold()
    needle = name.casefold()
    start = 0
    while True:
        position = lowered.find(needle, start)
        if position < 0:
            return False
        prefix = lowered[max(0, position - 72) : position]
        markers = ("do not", "don't", "avoid", "contraind", "not use", "exclude")
        if not any(marker in prefix for marker in markers):
            return False
        start = position + len(needle)


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
