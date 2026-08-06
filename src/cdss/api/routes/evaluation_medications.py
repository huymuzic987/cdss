"""Traversal-wide medication regimen aggregation for clinical presentation."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from cdss.api.routes.evaluation_medication_collection import (
    collect_action_type_ids,
    collect_payload,
    collect_text_ids,
    selected_classes,
)
from cdss.api.routes.evaluation_medication_values import (
    medicine_identity,
    medicine_json,
    option_medicine_ids,
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
from cdss.domain.decision_tree.medicine_catalog import Medicine, MedicineRepository
from cdss.domain.medication_safety_catalog import (
    filter_catalog_medicines,
    filter_raw_medicines,
)
from cdss.domain.medication_safety_resolver import (
    filter_medicine_options,
    resolve_safe_regimens,
)


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
        _merge_regimen(
            action,
            medicines,
            options,
            safe_catalog,
            runtime_input,
            regimen_plan=regimen_plan.model_dump(mode="json"),
        )
        for action in actions
    ]


def _merge_regimen(
    action: ExecutedAction,
    traversed_medicines: list[JsonObject],
    traversed_options: list[JsonObject],
    catalog: list[Medicine],
    runtime_input: Mapping[str, Any],
    *,
    regimen_plan: JsonObject,
) -> ExecutedAction:
    payload = dict(action.payload)
    action_medicines: list[JsonObject] = []
    action_options: list[JsonObject] = []
    collect_payload(payload, medicines=action_medicines, options=action_options)
    options = unique_objects([*action_options, *traversed_options])
    context = "acute_emergency" if payload.get("target_timing") else "chronic_hypertension"
    options, safety = filter_medicine_options(options, runtime_input, clinical_context=context)
    represented_ids = option_medicine_ids(options)
    raw_medicines = [
        medicine
        for medicine in unique_medicines([*action_medicines, *traversed_medicines])
        if medicine_identity(medicine) not in represented_ids
    ]
    medicines, _ = filter_raw_medicines(
        raw_medicines,
        runtime_input,
        clinical_context=context,
    )
    for key in ("medicines", "medicine_options", "medicine_catalog_by_class"):
        payload.pop(key, None)
    if medicines:
        payload["medicines"] = medicines
    if options:
        payload["medicine_options"] = options
        payload["medication_safety"] = safety
    classes = selected_classes(medicines, options)
    if classes:
        payload["medicine_catalog_by_class"] = {
            code: [medicine_json(item) for item in catalog if item.drug_class == code]
            for code in sorted(classes)
        }
    if regimen_plan.get("steps"):
        payload["regimen_plan"] = deepcopy(regimen_plan)
    return action.model_copy(update={"payload": payload})


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
