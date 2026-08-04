"""JSON identity and deduplication helpers for medication presentation."""

import json
from copy import deepcopy

from cdss.domain.decision_tree import JsonObject
from cdss.domain.decision_tree.medicine_catalog import Medicine


def option_medicine_ids(options: list[JsonObject]) -> set[str]:
    identities: set[str] = set()
    for option in options:
        medicine_map = option.get("medicines")
        if not isinstance(medicine_map, dict):
            continue
        for values in medicine_map.values():
            if not isinstance(values, list):
                continue
            identities.update(
                identity
                for raw in values
                if isinstance(raw, dict)
                if (identity := medicine_identity(raw))
            )
    return identities


def unique_medicines(medicines: list[JsonObject]) -> list[JsonObject]:
    output: list[JsonObject] = []
    seen: set[str] = set()
    for medicine in medicines:
        key = medicine_identity(medicine)
        if key and key not in seen:
            seen.add(key)
            output.append(deepcopy(medicine))
    return output


def medicine_identity(medicine: JsonObject) -> str:
    identity = medicine.get("drug_id") or medicine.get("id")
    if not isinstance(identity, str) or not identity.strip():
        name = medicine.get("name") or medicine.get("drug_name")
        identity = name if isinstance(name, str) else ""
    return identity.casefold().strip()


def unique_objects(values: list[JsonObject]) -> list[JsonObject]:
    output: list[JsonObject] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if key not in seen:
            seen.add(key)
            output.append(deepcopy(value))
    return output


def medicine_json(medicine: Medicine) -> JsonObject:
    return {
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
