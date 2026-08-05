"""JSON identity and deduplication helpers for medication presentation."""

import json
from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree import JsonObject
from cdss.domain.decision_tree.contracts import copy_json_value
from cdss.domain.decision_tree.medicine_catalog import Medicine


def copy_json_object(value: object) -> JsonObject | None:
    """Detach nested frozen mappings before they enter medication processing."""

    if not isinstance(value, Mapping):
        return None
    copied = copy_json_value(value)
    return copied if isinstance(copied, dict) else None


def option_medicine_ids(options: list[JsonObject]) -> set[str]:
    identities: set[str] = set()
    for option in options:
        medicine_map = option.get("medicines")
        if not isinstance(medicine_map, Mapping):
            continue
        for values in medicine_map.values():
            if not isinstance(values, (list, tuple)):
                continue
            identities.update(
                identity
                for raw in values
                if isinstance(raw, Mapping)
                if (identity := medicine_identity(raw))
            )
    return identities


def unique_medicines(medicines: list[JsonObject]) -> list[JsonObject]:
    output: list[JsonObject] = []
    seen: set[str] = set()
    for medicine in medicines:
        normalized = copy_json_object(medicine)
        if normalized is None:
            continue
        key = medicine_identity(normalized)
        if key and key not in seen:
            seen.add(key)
            output.append(normalized)
    return output


def medicine_identity(medicine: Mapping[str, Any]) -> str:
    identity = medicine.get("drug_id") or medicine.get("id")
    if not isinstance(identity, str) or not identity.strip():
        name = medicine.get("name") or medicine.get("drug_name")
        identity = name if isinstance(name, str) else ""
    return identity.casefold().strip()


def unique_objects(values: list[JsonObject]) -> list[JsonObject]:
    output: list[JsonObject] = []
    seen: set[str] = set()
    for value in values:
        normalized = copy_json_object(value)
        if normalized is None:
            continue
        key = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if key not in seen:
            seen.add(key)
            output.append(normalized)
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
