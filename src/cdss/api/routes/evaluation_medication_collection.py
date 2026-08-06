"""Collect positive medication candidates from the traversal audit trail."""

from __future__ import annotations

import re
from collections.abc import Mapping

from cdss.api.routes.evaluation_medication_values import copy_json_object
from cdss.domain.decision_tree.contracts import JsonObject
from cdss.domain.decision_tree.medication_regimen_subgroups import (
    catalog_group_matches,
    subgroup_matches,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine

MRA_NAMES = frozenset({"eplerenone", "spironolactone"})
_INFERENCE_OPERATION_PATTERN = re.compile(r"_INFERENCE_([A-Z]+)(?:_|$)")
_TREATMENT_OPERATIONS = frozenset(
    {
        "START",
        "ADD",
        "COMBINE",
        "SELECT",
        "ADJUST",
        "CHANGE",
        "ESCALATE",
        "REDUCE",
        "STOP",
        "REMOVE",
        "KEEP",
        "MAINTAIN",
        "MONITOR",
        "AVOID",
        "RESTORE",
    }
)
_NON_POSITIVE_OPERATIONS = frozenset({"STOP", "REMOVE", "AVOID"})


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
    *,
    text: str = "",
) -> None:
    if not isinstance(action_payload, Mapping):
        return
    action_type = action_payload.get("action_type")
    if not isinstance(action_type, str):
        return
    recognition_text = f"{action_type} {text}"
    if _negative_action(action_type, recognition_text):
        return
    _collect_group_ids(recognition_text, catalog, output)


def collect_inference_group_ids(
    text: str,
    catalog: list[Medicine],
    output: set[str],
    *,
    node_key: str,
) -> None:
    """Collect medicines for treatment inferences from their vocabulary.

    Inference keys and text carry the operation and the clinical group. This
    keeps legacy nodes useful while letting catalog subgroup names drive the
    final medicine selection instead of maintaining an action-type table.
    """

    match = _INFERENCE_OPERATION_PATTERN.search(node_key)
    if not match or match.group(1) not in _TREATMENT_OPERATIONS:
        return
    operation = match.group(1)
    if operation in _NON_POSITIVE_OPERATIONS or _negative_action(operation, text):
        return
    _collect_group_ids(f"{node_key} {text}", catalog, output)


def _collect_group_ids(text: str, catalog: list[Medicine], output: set[str]) -> None:
    for selector, subgroups in catalog_group_matches(text, catalog):
        output.update(
            medicine.drug_id
            for medicine in catalog
            if medicine.available and matches_selector(medicine, selector, subgroups)
        )


def matches_selector(
    medicine: Medicine,
    selector: str,
    subgroups: str | None = None,
) -> bool:
    if selector == "MRA":
        belongs_to_mra = medicine.name.casefold().strip() in MRA_NAMES or (
            medicine.subgroup is not None and "MRA" in medicine.subgroup.upper()
        )
        return belongs_to_mra and (
            subgroups is None or subgroup_matches(medicine.subgroup, subgroups)
        )
    drug_class = medicine.drug_class
    return (
        isinstance(drug_class, str)
        and drug_class.casefold() == selector.casefold()
        and (subgroups is None or subgroup_matches(medicine.subgroup, subgroups))
    )


def _negative_action(action_type: str, text: str) -> bool:
    action = action_type.strip().upper()
    if action.startswith(("NO_", "AVOID", "STOP", "REMOVE", "DISCONTINUE", "EXCLUDE")):
        return True
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "do not",
            "don't",
            "avoid",
            "contraind",
            "not use",
            "no routine",
            "exclude",
            "discontinue",
            "stop",
        )
    )


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
