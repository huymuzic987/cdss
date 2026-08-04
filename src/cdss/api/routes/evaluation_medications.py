"""Traversal-wide medication regimen aggregation for clinical presentation."""

from collections.abc import Mapping
from copy import deepcopy

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
)
from cdss.domain.decision_tree.drug_classes import build_medicine_options
from cdss.domain.decision_tree.medicine_catalog import Medicine, MedicineRepository

_ACTION_TYPE_CLASSES: dict[str, tuple[str, ...]] = {
    "COMBINE_D_SGLT2I_ALDO": ("D", "SGLT2i", "MRA"),
    "COMBINE_ABD_ALDO_SGLT2I": ("A", "B", "D", "SGLT2i", "MRA"),
    "ADD_A_ARNI_CTTA_UCMC": ("A",),
}
_MRA_NAMES = frozenset({"eplerenone", "spironolactone"})


def enrich_inferred_medications(
    actions: list[ExecutedAction],
    result: TraversalResult,
    repository: TreeGraphRepository,
    medicine_repository: MedicineRepository,
) -> list[ExecutedAction]:
    """Carry every positive medication/regimen reached by traversal to the output."""

    catalog = list(medicine_repository.list_all())
    drug_ids: set[str] = set()
    medicines: list[JsonObject] = []
    options: list[JsonObject] = []
    for executed in result.actions:
        _collect_payload(executed.payload, medicines=medicines, options=options)
        _collect_text_ids(f"{executed.text_en} {executed.text_vi}", catalog, drug_ids)
    for entry in result.trace:
        if entry.event is not TraceEvent.NODE_ENTERED:
            continue
        try:
            node = repository.get_tree(entry.tree_key).nodes_by_key[entry.node_key]
        except (DecisionTreeError, KeyError):
            continue
        _collect_text_ids(f"{node.text_en} {node.text_vi}", catalog, drug_ids)
        _collect_action_type_ids(
            getattr(node, "action_payload", None),
            catalog,
            drug_ids,
        )

    maintains = any(
        "_INFERENCE_MAINTAIN_" in entry.node_key
        for entry in result.trace
        if entry.event is TraceEvent.NODE_ENTERED
    )
    context_options = (
        None if maintains else build_medicine_options(result.context, medicine_repository)
    )
    if context_options:
        options.extend(context_options)
    options = unique_objects(options)
    medicines.extend(medicine_json(item) for item in catalog if item.drug_id in drug_ids)
    medicines = unique_medicines(medicines)
    regimen_plan = build_traversed_medication_regimen(
        result,
        repository,
        medicine_repository,
    )
    return [
        _merge_regimen(
            action,
            medicines,
            options,
            catalog,
            regimen_plan=regimen_plan.model_dump(mode="json"),
        )
        for action in actions
    ]


def _merge_regimen(
    action: ExecutedAction,
    traversed_medicines: list[JsonObject],
    traversed_options: list[JsonObject],
    catalog: list[Medicine],
    *,
    regimen_plan: JsonObject,
) -> ExecutedAction:
    payload = dict(action.payload)
    action_medicines: list[JsonObject] = []
    action_options: list[JsonObject] = []
    _collect_payload(payload, medicines=action_medicines, options=action_options)
    options = unique_objects([*action_options, *traversed_options])
    represented_ids = option_medicine_ids(options)
    medicines = [
        medicine
        for medicine in unique_medicines([*action_medicines, *traversed_medicines])
        if medicine_identity(medicine) not in represented_ids
    ]
    if medicines:
        payload["medicines"] = medicines
    if options:
        payload["medicine_options"] = options
    selected_classes = _selected_classes(medicines, options)
    if selected_classes:
        payload["medicine_catalog_by_class"] = {
            code: [medicine_json(item) for item in catalog if item.drug_class == code]
            for code in sorted(selected_classes)
        }
    if regimen_plan.get("steps"):
        payload["regimen_plan"] = deepcopy(regimen_plan)
    return action.model_copy(update={"payload": payload})


def _selected_classes(
    medicines: list[JsonObject],
    options: list[JsonObject],
) -> set[str]:
    selected: set[str] = set()
    for medicine in medicines:
        code = medicine.get("drug_class")
        if isinstance(code, str) and code in {"A", "B", "C", "D"}:
            selected.add(code)
    for option in options:
        classes = option.get("classes")
        if isinstance(classes, list):
            selected.update(
                code for code in classes if isinstance(code, str) and code in {"A", "B", "C", "D"}
            )
    return selected


def _collect_payload(
    payload: JsonObject,
    *,
    medicines: list[JsonObject],
    options: list[JsonObject],
) -> None:
    raw_medicines = payload.get("medicines")
    if isinstance(raw_medicines, list):
        medicines.extend(deepcopy(item) for item in raw_medicines if isinstance(item, dict))
    raw_options = payload.get("medicine_options")
    if isinstance(raw_options, list):
        options.extend(deepcopy(item) for item in raw_options if isinstance(item, dict))


def _collect_text_ids(text: str, catalog: list[Medicine], output: set[str]) -> None:
    lowered = text.casefold()
    for medicine in catalog:
        if medicine.name.casefold() in lowered and not _negated(medicine.name, lowered):
            output.add(medicine.drug_id)


def _collect_action_type_ids(
    action_payload: object,
    catalog: list[Medicine],
    output: set[str],
) -> None:
    if not isinstance(action_payload, Mapping):
        return
    action_type = action_payload.get("action_type")
    if not isinstance(action_type, str):
        return
    for selector in _ACTION_TYPE_CLASSES.get(action_type, ()):
        output.update(
            medicine.drug_id
            for medicine in catalog
            if medicine.available and _matches_selector(medicine, selector)
        )


def _matches_selector(medicine: Medicine, selector: str) -> bool:
    if selector == "MRA":
        return medicine.name.casefold().strip() in _MRA_NAMES
    drug_class = medicine.drug_class
    return isinstance(drug_class, str) and drug_class.casefold() == selector.casefold()


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
