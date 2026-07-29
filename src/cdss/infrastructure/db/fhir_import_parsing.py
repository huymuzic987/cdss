"""Defensive extraction of primitive values from clinical FHIR resources."""

from datetime import date
from typing import Any


def extension_value(extensions: list[dict[str, Any]], url: str) -> Any:
    for ext in extensions:
        if ext.get("url") != url:
            continue
        for key in ("valueString", "valueInteger", "valueBoolean", "valueDate"):
            if key in ext:
                return ext[key]
    return None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def reference_id(reference: str | None) -> str | None:
    if not reference or "/" not in reference:
        return None
    return reference.split("/", 1)[1]


def drug_class_note(medication_request: dict[str, Any]) -> str | None:
    for note in medication_request.get("note") or []:
        text = note.get("text", "")
        if text.startswith("drugClass:"):
            return text.split(":", 1)[1].strip()
    return None


def medication_dose(medication_request: dict[str, Any]) -> tuple[float | None, str | None]:
    dosage = medication_request.get("dosageInstruction") or []
    if not dosage:
        return None, None
    dose_and_rate = dosage[0].get("doseAndRate") or []
    if not dose_and_rate:
        return None, None
    quantity = dose_and_rate[0].get("doseQuantity") or {}
    return quantity.get("value"), quantity.get("unit")
