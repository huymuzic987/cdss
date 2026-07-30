"""Build the stable presentation contract consumed by the CDS modal."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from cdss.api.schemas.clinical_evaluation import ParsedClinicalBundle
from cdss.domain.decision_tree import (
    ExecutedAction,
    ExecutedReference,
    JsonObject,
    TraversalTraceEntry,
)

_CLINICAL_FINDING_LABELS: dict[str, tuple[str, str]] = {
    "has_target_organ_damage": ("Target-organ damage", "Tổn thương cơ quan đích"),
    "has_mi_acs": (
        "Myocardial infarction / acute coronary syndrome",
        "Nhồi máu cơ tim / hội chứng vành cấp",
    ),
    "has_acute_coronary_syndrome": (
        "Acute coronary syndrome",
        "Hội chứng vành cấp",
    ),
    "has_cardiovascular_disease": ("Cardiovascular disease", "Bệnh tim mạch"),
    "has_coronary_artery_disease": ("Coronary artery disease", "Bệnh mạch vành"),
    "has_stroke": ("Stroke", "Đột quỵ"),
    "has_tia": ("Transient ischemic attack", "Cơn thiếu máu não thoáng qua"),
    "has_type_2_diabetes": ("Type 2 diabetes", "Đái tháo đường type 2"),
    "has_diabetes": ("Diabetes", "Đái tháo đường"),
    "has_heart_failure": ("Heart failure", "Suy tim"),
    "has_hfref": (
        "Heart failure with reduced ejection fraction",
        "Suy tim phân suất tống máu giảm",
    ),
    "has_hfmref": (
        "Heart failure with mildly reduced ejection fraction",
        "Suy tim phân suất tống máu giảm nhẹ",
    ),
    "has_hfpef": (
        "Heart failure with preserved ejection fraction",
        "Suy tim phân suất tống máu bảo tồn",
    ),
    "has_ckd": ("Chronic kidney disease", "Bệnh thận mạn"),
    "has_ckd_stage_3_or_higher": (
        "Chronic kidney disease stage 3 or higher",
        "Bệnh thận mạn giai đoạn 3 trở lên",
    ),
    "has_kidney_transplant": ("Kidney transplant", "Ghép thận"),
    "is_pregnant": ("Pregnancy", "Mang thai"),
    "is_postpartum": ("Postpartum", "Sau sinh"),
    "is_breastfeeding": ("Breastfeeding", "Đang cho con bú"),
    "has_hypertensive_crisis": ("Hypertensive crisis", "Cơn tăng huyết áp"),
    "has_acute_ischemic_stroke": ("Acute ischemic stroke", "Đột quỵ thiếu máu cấp"),
    "has_acute_aortic_syndrome": ("Acute aortic syndrome", "Hội chứng động mạch chủ cấp"),
    "has_hypertensive_encephalopathy": (
        "Hypertensive encephalopathy",
        "Bệnh não do tăng huyết áp",
    ),
    "has_acute_intracerebral_hemorrhage": (
        "Acute intracerebral hemorrhage",
        "Xuất huyết não cấp",
    ),
    "has_acute_cardiogenic_pulmonary_edema": (
        "Acute cardiogenic pulmonary edema",
        "Phù phổi cấp do tim",
    ),
    "has_eclampsia_severe_preeclampsia_or_hellp": (
        "Eclampsia, severe preeclampsia, or HELLP syndrome",
        "Sản giật, tiền sản giật nặng hoặc hội chứng HELLP",
    ),
}

_RISK_LEVEL_LABELS: dict[str, tuple[str, str]] = {
    "LOW": ("Low Hypertension Risk", "Nguy cơ tăng huyết áp thấp"),
    "MEDIUM": ("Moderate Hypertension Risk", "Nguy cơ tăng huyết áp trung bình"),
    "MODERATE": ("Moderate Hypertension Risk", "Nguy cơ tăng huyết áp trung bình"),
    "HIGH": ("High Hypertension Risk", "Nguy cơ tăng huyết áp cao"),
    "VERY_HIGH": ("Very High Hypertension Risk", "Nguy cơ tăng huyết áp rất cao"),
}

_EMERGENCY_BRANCH_NODE = "T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE"
_URGENCY_BRANCH_NODES = {
    "T14_C_NO_ACUTE_TARGET_ORGAN_DAMAGE",
    "T14_END_URGENT_HYPERTENSION",
}


def attach_terminal_presentation(
    actions: list[ExecutedAction],
    parsed: ParsedClinicalBundle,
    references: list[ExecutedReference],
    trace: list[TraversalTraceEntry] | None = None,
    context: JsonObject | None = None,
) -> list[ExecutedAction]:
    output = [action.model_copy(deep=True) for action in actions]
    if not output:
        return output
    terminal = output[-1]
    terminal.payload["presentation"] = build_presentation(
        terminal,
        parsed,
        references,
        trace=trace,
        context=context,
    )
    return output


def build_presentation(
    action: ExecutedAction,
    parsed: ParsedClinicalBundle,
    references: list[ExecutedReference],
    *,
    trace: list[TraversalTraceEntry] | None = None,
    context: JsonObject | None = None,
) -> JsonObject:
    payload = action.payload
    strategy_references = _treatment_preference_references(references, trace or [])
    presentation: JsonObject = {
        "schema_version": "1.0",
        "alert": {
            "text_en": _string(payload.get("alert_en"), "Clinical decision support recommendation"),
            "text_vi": _string(payload.get("alert_vi"), "Khuyến nghị hỗ trợ quyết định lâm sàng"),
        },
        "alert_summary": _alert_summary(parsed, trace or [], context or {}),
        "trigger_evidence": [deepcopy(item) for item in parsed.trigger_evidence],
        "recommendation": {"text_en": action.text_en, "text_vi": action.text_vi},
        "recommended_orders": _recommended_orders(action, strategy_references),
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


def _alert_summary(
    parsed: ParsedClinicalBundle,
    trace: list[TraversalTraceEntry],
    context: JsonObject,
) -> JsonObject:
    crisis_classification = _hypertensive_crisis_classification(trace)
    risk_level = _traversed_risk_level(trace, context)
    findings: list[JsonObject] = []
    seen_codes: set[str] = set()
    for entry in trace:
        if entry.event.value != "candidate_evaluated" or entry.condition_result is not True:
            continue
        for path in _condition_paths(entry.condition_definition):
            if not path.startswith("input."):
                continue
            code = path.removeprefix("input.")
            labels = _CLINICAL_FINDING_LABELS.get(code)
            if (
                labels is None
                or (crisis_classification is not None and code == "has_hypertensive_crisis")
                or parsed.runtime_input.get(code) is not True
                or code in seen_codes
            ):
                continue
            seen_codes.add(code)
            findings.append(
                {
                    "code": code,
                    "label_en": labels[0],
                    "label_vi": labels[1],
                    "tree_key": entry.tree_key,
                    "node_key": entry.candidate_node_key or entry.node_key,
                }
            )

    summary_items = [
        item for item in (crisis_classification, risk_level) if item is not None
    ]
    labels_en = [str(item["label_en"]) for item in summary_items]
    labels_vi = [str(item["label_vi"]) for item in summary_items]
    summary: JsonObject = {
        "text_en": (
            f"Patient has {', '.join(labels_en)}"
            if labels_en
            else "Patient has clinical findings requiring review."
        ),
        "text_vi": (
            f"Bệnh nhân có {', '.join(labels_vi)}"
            if labels_vi
            else "Bệnh nhân có các phát hiện lâm sàng cần được đánh giá."
        ),
        "findings": findings,
    }
    if crisis_classification is not None:
        summary["hypertensive_crisis_classification"] = crisis_classification
    if risk_level is not None:
        summary["risk_level"] = risk_level
    return summary


def _traversed_risk_level(
    trace: list[TraversalTraceEntry],
    context: JsonObject,
) -> JsonObject | None:
    was_classified = any(
        entry.event.value == "node_entered"
        and entry.tree_key == "risk-classification"
        and entry.node_type.value == "INFERENCE"
        and any(
            path == "context.risk.level" or path.startswith("context.risk.level.")
            for path in entry.changed_context_paths
        )
        for entry in trace
    )
    risk = context.get("risk")
    if not was_classified or not isinstance(risk, dict):
        return None
    value = risk.get("level")
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    labels = _RISK_LEVEL_LABELS.get(code)
    if labels is None:
        return None
    return {"code": code, "label_en": labels[0], "label_vi": labels[1]}


def _hypertensive_crisis_classification(
    trace: list[TraversalTraceEntry],
) -> JsonObject | None:
    entered_nodes = {
        entry.node_key
        for entry in trace
        if entry.event.value == "node_entered"
        and entry.tree_key == "hypertensive-emergency"
    }
    if _EMERGENCY_BRANCH_NODE in entered_nodes:
        return {
            "code": "EMERGENCY_HYPERTENSION",
            "label_en": "Emergency Hypertension",
            "label_vi": "Tăng huyết áp cấp cứu",
        }
    if entered_nodes.intersection(_URGENCY_BRANCH_NODES):
        return {
            "code": "URGENCY_HTN",
            "label_en": "Urgency Hypertension",
            "label_vi": "Tăng huyết áp khẩn trương",
        }
    return None


def _condition_paths(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    paths: list[str] = []
    path = value.get("path")
    if isinstance(path, str):
        paths.append(path)
    for key in ("all", "any"):
        children = value.get(key)
        if isinstance(children, list):
            for child in children:
                paths.extend(_condition_paths(child))
    nested = value.get("not")
    if isinstance(nested, dict):
        paths.extend(_condition_paths(nested))
    return paths


def _treatment_preference_references(
    references: list[ExecutedReference],
    trace: list[TraversalTraceEntry],
) -> list[ExecutedReference]:
    provenance = {
        (entry.tree_key, entry.node_key)
        for entry in trace
        if (
            entry.event.value == "node_entered"
            and entry.node_type.value == "INFERENCE"
            and any(
                path == "context.treatment_preferences"
                or path.startswith("context.treatment_preferences.")
                for path in entry.changed_context_paths
            )
        )
    }
    return [
        reference
        for reference in references
        if (reference.tree_key, reference.node_key) in provenance
    ]


def _recommended_orders(
    action: ExecutedAction,
    strategy_references: list[ExecutedReference],
) -> list[JsonObject]:
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
            dose_strategy = _string(
                raw.get("dose_strategy"),
                _string(payload.get("dose_strategy"), "LOW_TO_USUAL_DOSE"),
            )
            drug_classes = _drug_class_details(raw, classes, dose_strategy)
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
                    "strategy_references": [
                        _guideline_reference(reference) for reference in strategy_references
                    ],
                    "source_data": deepcopy(raw),
                }
            )
    return orders


def _drug_class_details(
    option: JsonObject, classes: list[str], dose_strategy: str
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
                if not isinstance(raw, dict) or raw.get("available") is False:
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
        "tree_key": reference.tree_key,
        "tree_name_en": reference.tree_name_en,
        "tree_name_vi": reference.tree_name_vi,
        "node_key": reference.node_key,
        "node_text_en": reference.node_text_en,
        "node_text_vi": reference.node_text_vi,
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
