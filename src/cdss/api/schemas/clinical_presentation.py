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
    existing = payload.get("recommended_orders")
    if isinstance(existing, list):
        return [deepcopy(item) for item in existing if isinstance(item, dict)]
    orders: list[JsonObject] = []
    medicines = payload.get("medicines")
    if isinstance(medicines, list):
        for index, raw in enumerate(medicines):
            if not isinstance(raw, dict) or raw.get("available") is False:
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
            orders.append(
                {
                    "id": f"{action.node_key}-combination-{index}",
                    "type": "medication",
                    "name_en": " + ".join(classes) or "Medication combination",
                    "name_vi": " + ".join(classes) or "Phối hợp thuốc",
                    "class_label_en": " + ".join(classes),
                    "class_label_vi": " + ".join(classes),
                    "source_data": deepcopy(raw),
                }
            )
    return orders


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
