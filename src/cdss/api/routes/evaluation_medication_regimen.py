"""Merge the traversal-derived regimen into the terminal presentation."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from cdss.api.routes.evaluation_medication_collection import (
    MEDICATION_GROUPS,
    collect_payload,
    selected_classes,
)
from cdss.api.routes.evaluation_medication_values import (
    medicine_identity,
    medicine_json,
    option_medicine_ids,
    unique_medicines,
    unique_objects,
)
from cdss.domain.decision_tree import ExecutedAction, JsonObject
from cdss.domain.decision_tree.medicine_catalog import Medicine
from cdss.domain.medication_safety.medication_safety_catalog import filter_raw_medicines
from cdss.domain.medication_safety.medication_safety_resolver import filter_medicine_options


def merge_regimen(
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
    plan_catalog_by_class = regimen_plan.get("catalog_by_class")
    if isinstance(plan_catalog_by_class, Mapping):
        classes.update(
            code
            for code in plan_catalog_by_class
            if isinstance(code, str) and code in MEDICATION_GROUPS
        )
    if classes:
        payload["medicine_catalog_by_class"] = {
            code: (
                plan_catalog_by_class[code]
                if isinstance(plan_catalog_by_class, Mapping)
                and isinstance(plan_catalog_by_class.get(code), list)
                else [medicine_json(item) for item in catalog if item.drug_class == code]
            )
            for code in sorted(classes)
        }
    if regimen_plan.get("steps"):
        payload["regimen_plan"] = deepcopy(regimen_plan)
    return action.model_copy(update={"payload": payload})
