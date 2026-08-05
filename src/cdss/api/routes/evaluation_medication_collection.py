"""Collect positive medication candidates from the traversal audit trail."""

from __future__ import annotations

from collections.abc import Mapping

from cdss.api.routes.evaluation_medication_values import copy_json_object
from cdss.domain.decision_tree.contracts import JsonObject
from cdss.domain.decision_tree.medicine_catalog import Medicine

ACTION_TYPE_CLASSES: dict[str, tuple[str, ...]] = {
    "COMBINE_D_SGLT2I_ALDO": ("D", "SGLT2i", "MRA"),
    "COMBINE_ABD_ALDO_SGLT2I": ("A", "B", "D", "SGLT2i", "MRA"),
    "ADD_A_ARNI_CTTA_UCMC": ("A",),
}
MRA_NAMES = frozenset({"eplerenone", "spironolactone"})


def collect_payload(
    payload: JsonObject,
    *,
    medicines: list[JsonObject],
    options: list[JsonObject],
) -> None:
    raw_medicines = payload.get("medicines")
    if isinstance(raw_medicines, (list, tuple)):
        medicines.extend(
            copied for item in raw_medicines if (copied := copy_json_object(item)) is not None
        )
    raw_options = payload.get("medicine_options")
    if isinstance(raw_options, (list, tuple)):
        options.extend(
            copied for item in raw_options if (copied := copy_json_object(item)) is not None
        )


def selected_classes(medicines: list[JsonObject], options: list[JsonObject]) -> set[str]:
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


def collect_text_ids(text: str, catalog: list[Medicine], output: set[str]) -> None:
    lowered = text.casefold()
    for medicine in catalog:
        if medicine.name.casefold() in lowered and not negated(medicine.name, lowered):
            output.add(medicine.drug_id)


def collect_action_type_ids(
    action_payload: object,
    catalog: list[Medicine],
    output: set[str],
) -> None:
    if not isinstance(action_payload, Mapping):
        return
    action_type = action_payload.get("action_type")
    if not isinstance(action_type, str):
        return
    for selector in ACTION_TYPE_CLASSES.get(action_type, ()):
        output.update(
            medicine.drug_id
            for medicine in catalog
            if medicine.available and matches_selector(medicine, selector)
        )


def matches_selector(medicine: Medicine, selector: str) -> bool:
    if selector == "MRA":
        return medicine.name.casefold().strip() in MRA_NAMES
    drug_class = medicine.drug_class
    return isinstance(drug_class, str) and drug_class.casefold() == selector.casefold()


def negated(name: str, text: str) -> bool:
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
        "khÃ´ng dÃ¹ng",
        "trÃ¡nh",
        "chá»‘ng chá»‰ Ä‘á»‹nh",
        "loáº¡i trá»«",
        "ngá»«ng",
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
