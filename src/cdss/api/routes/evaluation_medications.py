"""Traversal-wide medication regimen aggregation for clinical presentation."""

from cdss.api.routes.evaluation_medication_collection import (
    collect_action_type_ids,
    collect_inference_group_ids,
    collect_payload,
    collect_text_ids,
)
from cdss.api.routes.evaluation_medication_regimen import merge_regimen
from cdss.api.routes.evaluation_medication_values import (
    medicine_json,
    unique_medicines,
    unique_objects,
)
from cdss.domain.decision_tree import (
    DecisionTreeError,
    ExecutedAction,
    JsonObject,
    TraceEvent,
    TraversalResult,
    TreeGraphRepository,
    build_traversed_medication_regimen,
    filter_medication_regimen_plan,
)
from cdss.domain.decision_tree.medicine_catalog import MedicineRepository
from cdss.domain.medication_safety.medication_safety_catalog import (
    filter_catalog_medicines,
    filter_raw_medicines,
)
from cdss.domain.medication_safety.medication_safety_resolver import resolve_safe_regimens


def enrich_inferred_medications(
    actions: list[ExecutedAction],
    result: TraversalResult,
    repository: TreeGraphRepository,
    medicine_repository: MedicineRepository,
) -> list[ExecutedAction]:
    """Carry every positive medication/regimen reached by traversal to the output."""

    catalog = list(medicine_repository.list_all())
    clinical_context = (
        "acute_emergency"
        if any(entry.payload.get("target_timing") for entry in result.actions)
        else "chronic_hypertension"
    )
    runtime_input = getattr(result, "input_snapshot", {})
    safe_catalog = filter_catalog_medicines(
        catalog, runtime_input, clinical_context=clinical_context
    )
    drug_ids: set[str] = set()
    medicines: list[JsonObject] = []
    options: list[JsonObject] = []
    for executed in result.actions:
        collect_payload(executed.payload, medicines=medicines, options=options)
        collect_text_ids(f"{executed.text_en} {executed.text_vi}", catalog, drug_ids)
    for entry in result.trace:
        if entry.event is not TraceEvent.NODE_ENTERED:
            continue
        try:
            node = repository.get_tree(entry.tree_key).nodes_by_key[entry.node_key]
        except (DecisionTreeError, KeyError):
            continue
        collect_text_ids(f"{node.text_en} {node.text_vi}", catalog, drug_ids)
        collect_action_type_ids(
            getattr(node, "action_payload", None),
            catalog,
            drug_ids,
            text=f"{node.text_en} {node.text_vi}",
        )
        collect_inference_group_ids(
            f"{node.text_en} {node.text_vi}",
            catalog,
            drug_ids,
            node_key=entry.node_key,
        )

    medicines, _ = filter_raw_medicines(medicines, runtime_input, clinical_context=clinical_context)

    maintains = any(
        "_INFERENCE_MAINTAIN_" in entry.node_key
        for entry in result.trace
        if entry.event is TraceEvent.NODE_ENTERED
    )
    context_options = (
        None
        if maintains
        else resolve_safe_regimens(
            {"action_type": "INITIAL_TWO_DRUG_COMBINATION"},
            result.context,
            runtime_input,
            medicine_repository,
        )[0]
    )
    if context_options:
        options.extend(context_options)
    options = unique_objects(options)
    medicines.extend(medicine_json(item) for item in safe_catalog if item.drug_id in drug_ids)
    medicines = unique_medicines(medicines)
    regimen_plan = build_traversed_medication_regimen(
        result,
        repository,
        medicine_repository,
    )
    regimen_plan = filter_medication_regimen_plan(regimen_plan, runtime_input)
    return [
        merge_regimen(
            action,
            medicines,
            options,
            safe_catalog,
            runtime_input,
            regimen_plan=regimen_plan.model_dump(mode="json"),
        )
        for action in actions
    ]


def _negated(name: str, text: str) -> bool:
    """Return true only when every occurrence is safety/stop language."""

    lowered = text.casefold()
    needle = name.casefold()
    start = 0
    found = False
    markers = (
        "do not",
        "don't",
        "avoid",
        "contraind",
        "not use",
        "exclude",
        "discontinue",
        "stop",
        "không dùng",
        "tránh",
        "chống chỉ định",
        "loại trừ",
        "ngừng",
    )
    while True:
        position = lowered.find(needle, start)
        if position < 0:
            return found
        found = True
        prefix = lowered[max(0, position - 72) : position]
        if not any(marker in prefix for marker in markers):
            return False
        start = position + len(needle)
