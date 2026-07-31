"""Build the stable presentation contract consumed by the CDS modal."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from cdss.api.schemas.clinical_evaluation import ParsedClinicalBundle
from cdss.domain.decision_tree import ExecutedAction, ExecutedReference, JsonObject


def attach_terminal_presentation(
    actions: list[ExecutedAction],
    parsed: ParsedClinicalBundle,
    references: list[ExecutedReference],
) -> list[ExecutedAction]:
    output = [action.model_copy(deep=True) for action in actions]
    if not output:
        return output
    terminal = output[-1]
    terminal.payload["presentation"] = build_presentation(terminal, parsed, references)
    return output


def build_presentation(
    action: ExecutedAction,
    parsed: ParsedClinicalBundle,
    references: list[ExecutedReference],
) -> JsonObject:
    payload = action.payload
    presentation: JsonObject = {
        "schema_version": "1.0",
        "alert": {
            "text_en": _string(payload.get("alert_en"), "Clinical decision support recommendation"),
            "text_vi": _string(payload.get("alert_vi"), "Khuyến nghị hỗ trợ quyết định lâm sàng"),
        },
        "trigger_evidence": [deepcopy(item) for item in parsed.trigger_evidence],
        "recommendation": {"text_en": action.text_en, "text_vi": action.text_vi},
        "recommended_orders": _recommended_orders(action),
        "additional_actions": _additional_actions(payload),
        "acknowledgement_options": _acknowledgements(),
        "clinical_details": [deepcopy(item) for item in parsed.clinical_details],
        "guideline_references": [_guideline_reference(reference) for reference in references],
    }
    if isinstance(payload.get("recommendation_strength"), str):
        presentation["evidence_strength"] = _coded_label(payload["recommendation_strength"])
    if isinstance(payload.get("evidence_level"), str):
        presentation["evidence_level"] = _coded_label(payload["evidence_level"])
    return presentation


def _recommended_orders(action: ExecutedAction) -> list[JsonObject]:
    payload = action.payload
    excluded = _excluded_medicines(payload)
    blocked_text = f"{_presentation_text(payload)} {action.text_en} {action.text_vi}".casefold()
    existing = payload.get("recommended_orders")
    if isinstance(existing, list):
        return [deepcopy(item) for item in existing if isinstance(item, dict)]
    orders: list[JsonObject] = []
    medicines = payload.get("medicines")
    if isinstance(medicines, list):
        for index, raw in enumerate(medicines):
            if (
                not isinstance(raw, dict)
                or raw.get("available") is False
                or _medicine_name(raw) in excluded
            ):
                continue
            name = _string(raw.get("name"), _string(raw.get("drug_name"), "Medication"))
            drug_id = _string(raw.get("drug_id"), _string(raw.get("id"), f"medicine-{index}"))
            orders.append(
                {
                    "id": f"{action.node_key}-medicine-{drug_id}",
                    "type": "medication",
                    "name_en": name,
                    "name_vi": name,
                    "dose": _string(
                        raw.get("starting_dose"),
                        _string(raw.get("dose_low"), _string(raw.get("dose"))),
                    ),
                    "class_label_en": _string(
                        raw.get("class_label"), _string(raw.get("drug_class"))
                    ),
                    "class_label_vi": _string(
                        raw.get("class_label_vi"),
                        _string(raw.get("class_label"), _string(raw.get("drug_class"))),
                    ),
                    "medicine_ids": [drug_id] if drug_id else [],
                    "source_data": deepcopy(raw),
                }
            )
    options = payload.get("medicine_options")
    if isinstance(options, list):
        for index, raw in enumerate(options):
            if not isinstance(raw, dict):
                continue
            classes = [str(item) for item in raw.get("classes", []) if isinstance(item, str)]
            dose_strategy = _string(
                raw.get("dose_strategy"),
                _string(payload.get("dose_strategy"), "LOW_TO_USUAL_DOSE"),
            )
            drug_classes = _drug_class_details(raw, classes, dose_strategy, excluded, blocked_text)
            labels_en = [f"Drug Class {code}" for code in classes]
            labels_vi = [f"Nhóm thuốc {code}" for code in classes]
            orders.append(
                {
                    "id": f"{action.node_key}-combination-{index}",
                    "type": "medication",
                    "name_en": " + ".join(labels_en) or "Medication combination",
                    "name_vi": " + ".join(labels_vi) or "Phối hợp thuốc",
                    "class_label_en": " + ".join(labels_en),
                    "class_label_vi": " + ".join(labels_vi),
                    "dose_strategy": dose_strategy,
                    "drug_classes": drug_classes,
                    "source_data": deepcopy(raw),
                }
            )
    return orders


def _drug_class_details(
    option: JsonObject,
    classes: list[str],
    dose_strategy: str,
    excluded: set[str],
    blocked_text: str,
) -> list[JsonObject]:
    medicine_map = option.get("medicines")
    if not isinstance(medicine_map, dict):
        medicine_map = {}
    result: list[JsonObject] = []
    for code in classes:
        raw_medicines = medicine_map.get(code)
        medicines: list[JsonObject] = []
        if isinstance(raw_medicines, list):
            for index, raw in enumerate(raw_medicines):
                if (
                    not isinstance(raw, dict)
                    or raw.get("available") is False
                    or _medicine_name(raw) in excluded
                    or _is_negated(_medicine_name(raw), blocked_text)
                ):
                    continue
                name = _string(raw.get("name"), _string(raw.get("drug_name")))
                if not name:
                    continue
                medicines.append(
                    {
                        "id": _string(raw.get("drug_id"), f"{code}-medicine-{index}"),
                        "name": name,
                        "dose": _dose_for_strategy(raw, dose_strategy),
                        "route": _string(raw.get("route")),
                        "subgroup": _string(raw.get("subgroup")),
                    }
                )
        result.append(
            {
                "code": code,
                "label_en": f"Drug Class {code}",
                "label_vi": f"Nhóm thuốc {code}",
                "dose_strategy": dose_strategy,
                "dose_label_en": _dose_strategy_label(dose_strategy, "en"),
                "dose_label_vi": _dose_strategy_label(dose_strategy, "vi"),
                "medicines": medicines,
            }
        )
    return result


def _medicine_name(raw: JsonObject) -> str:
    value = raw.get("name") or raw.get("drug_name")
    return value.casefold().strip() if isinstance(value, str) else ""


def _excluded_medicines(payload: JsonObject) -> set[str]:
    combined = _presentation_text(payload)
    excluded: set[str] = set()
    for raw in payload.get("medicines", []) if isinstance(payload.get("medicines"), list) else []:
        if isinstance(raw, dict):
            name = _medicine_name(raw)
            if name and _is_negated(name, combined):
                excluded.add(name)
    return excluded


def _presentation_text(payload: JsonObject) -> str:
    texts: list[str] = []
    for key in ("text_en", "text_vi"):
        value = payload.get(key)
        if isinstance(value, str):
            texts.append(value.casefold())
    for key in ("regimen_summary", "safety_notes"):
        values = payload.get(key)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    texts.extend(
                        str(value.get(key_name, "")).casefold()
                        for key_name in ("text_en", "text_vi")
                    )
    return " ".join(texts)


def _is_negated(name: str, text: str) -> bool:
    position = text.find(name)
    if position < 0:
        return False
    prefix = text[max(0, position - 72) : position]
    markers = ("do not", "don't", "avoid", "contraind", "not use", "exclude")
    return any(marker in prefix for marker in markers)


def _dose_for_strategy(medicine: JsonObject, strategy: str) -> str:
    low = _string(medicine.get("dose_low"))
    usual = _string(medicine.get("dose_usual"))
    maximum = _string(medicine.get("dose_max"))
    if strategy == "LOW_DOSE":
        return low
    if strategy == "LOW_TO_USUAL_DOSE":
        if low and usual and low != usual:
            return f"{low} → {usual}"
        return low or usual
    if strategy in {"USUAL_DOSE", "USUAL_DOSE_OR_ESCALATED_COMBINATION"}:
        return usual or low
    if strategy == "MAX_DOSE":
        return maximum or usual or low
    return _string(medicine.get("starting_dose"), low or usual)


def _dose_strategy_label(strategy: str, locale: str) -> str:
    labels = {
        "LOW_DOSE": ("Low dose", "Liều thấp"),
        "LOW_TO_USUAL_DOSE": ("Low to usual dose", "Liều thấp đến liều thông thường"),
        "USUAL_DOSE": ("Usual dose", "Liều thông thường"),
        "USUAL_DOSE_OR_ESCALATED_COMBINATION": (
            "Usual dose",
            "Liều thông thường",
        ),
        "MAX_DOSE": ("Maximum dose", "Liều tối đa"),
    }
    label = labels.get(strategy, (_humanize(strategy), _humanize(strategy)))
    return label[1] if locale == "vi" else label[0]


def _additional_actions(payload: JsonObject) -> list[JsonObject]:
    values = payload.get("additional_actions")
    if not isinstance(values, list):
        return []
    result: list[JsonObject] = []
    for index, value in enumerate(values):
        if isinstance(value, str):
            result.append({"id": value, "label_en": _humanize(value), "label_vi": _humanize(value)})
        elif isinstance(value, dict):
            item = deepcopy(value)
            item.setdefault("id", f"action-{index}")
            item.setdefault("label_en", _humanize(str(item["id"])))
            item.setdefault("label_vi", item["label_en"])
            result.append(item)
    return result


def _acknowledgements() -> list[JsonObject]:
    return [
        {
            "id": "different-order-or-dose",
            "label_en": "Different order or dose",
            "label_vi": "Chọn thuốc hoặc liều khác",
            "requires_text": False,
        },
        {
            "id": "discuss-with-patient",
            "label_en": "Discuss with patient",
            "label_vi": "Trao đổi với người bệnh",
            "requires_text": False,
        },
        {
            "id": "review-chart",
            "label_en": "Review chart",
            "label_vi": "Xem lại hồ sơ",
            "requires_text": False,
        },
        {
            "id": "remind-next-visit",
            "label_en": "Remind at next visit",
            "label_vi": "Nhắc lại ở lần khám sau",
            "requires_text": False,
        },
        {"id": "other", "label_en": "Other", "label_vi": "Khác", "requires_text": True},
    ]


def _guideline_reference(reference: ExecutedReference) -> JsonObject:
    return {
        "id": f"{reference.tree_key}:{reference.node_key}:{reference.reference_order}",
        "title_en": reference.source_title,
        "title_vi": reference.source_title,
        "section_path": deepcopy(reference.section_path),
        "locator": reference.locator,
        "locator_detail": reference.locator_detail,
        "printed_page_numbers": deepcopy(reference.printed_page_numbers),
        "pdf_page_numbers": deepcopy(reference.pdf_page_numbers),
        "note": reference.reference_note,
    }


def _coded_label(value: str) -> JsonObject:
    return {"code": value, "label_en": _humanize(value), "label_vi": _humanize(value)}


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _string(value: Any, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback
