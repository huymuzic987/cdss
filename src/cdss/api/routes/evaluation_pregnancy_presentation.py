"""Pregnancy-specific action enrichment for the evaluation response."""

from collections.abc import Mapping

from cdss.domain.decision_tree import (
    ExecutedAction,
    JsonObject,
    NodeType,
    TraceEvent,
    TraversalResult,
    TreeGraph,
)

_PREGNANCY_TREE_KEY = "hypertension-in-pregnancy"


def enrich_pregnancy_action(
    action: ExecutedAction,
    result: TraversalResult,
    graph: TreeGraph,
) -> ExecutedAction:
    enriched = action.model_copy(deep=True)
    cutoff = next(
        (
            index
            for index, entry in enumerate(result.trace)
            if entry.event is TraceEvent.NODE_ENTERED
            and entry.tree_key == action.tree_key
            and entry.node_key == action.node_key
        ),
        len(result.trace) - 1,
    )
    seen: set[str] = set()
    regimen_summary: list[JsonObject] = []
    for entry in result.trace[: cutoff + 1]:
        if (
            entry.event is not TraceEvent.NODE_ENTERED
            or entry.tree_key != _PREGNANCY_TREE_KEY
            or entry.node_type is not NodeType.INFERENCE
            or entry.node_key in seen
        ):
            continue
        seen.add(entry.node_key)
        node = graph.nodes_by_key[entry.node_key]
        regimen_summary.append(
            {
                "id": entry.node_key,
                "text_en": node.text_en,
                "text_vi": node.text_vi,
            }
        )
    if regimen_summary:
        enriched.payload["regimen_summary"] = regimen_summary

    safety_notes = _pregnancy_safety_notes(graph.global_nodes)
    if safety_notes:
        enriched.payload["safety_notes"] = safety_notes
    enriched.text_en = _pregnancy_recommendation_text(
        action.text_en,
        regimen_summary,
        safety_notes,
        locale="en",
    )
    enriched.text_vi = _pregnancy_recommendation_text(
        action.text_vi,
        regimen_summary,
        safety_notes,
        locale="vi",
    )
    _append_pregnancy_safety_actions(enriched, safety_notes)
    return enriched


def _pregnancy_recommendation_text(
    recommendation: str,
    regimen_summary: list[JsonObject],
    safety_notes: list[JsonObject],
    *,
    locale: str,
) -> str:
    regimen_heading = "Recorded regimen" if locale == "en" else "Phác đồ đã ghi nhận"
    safety_heading = "Pregnancy safety" if locale == "en" else "An toàn thai kỳ"
    text_key = "text_en" if locale == "en" else "text_vi"
    sections = [recommendation]
    regimen_lines = [
        item[text_key] for item in regimen_summary if isinstance(item.get(text_key), str)
    ]
    safety_lines = [item[text_key] for item in safety_notes if isinstance(item.get(text_key), str)]
    if regimen_lines:
        sections.append(f"{regimen_heading}:\n- " + "\n- ".join(regimen_lines))
    if safety_lines:
        sections.append(f"{safety_heading}:\n- " + "\n- ".join(safety_lines))
    return "\n\n".join(sections)


def _append_pregnancy_safety_actions(
    action: ExecutedAction,
    safety_notes: list[JsonObject],
) -> None:
    existing = action.payload.get("additional_actions")
    additional_actions = list(existing) if isinstance(existing, list) else []
    for note in safety_notes:
        additional_actions.append(
            {
                "id": f"pregnancy-safety-{note['id']}",
                "label_en": note["text_en"],
                "label_vi": note["text_vi"],
            }
        )
    if additional_actions:
        action.payload["additional_actions"] = additional_actions


def _pregnancy_safety_notes(global_nodes) -> list[JsonObject]:
    notes: list[JsonObject] = []
    for node in global_nodes:
        config = node.global_config
        if not isinstance(config, Mapping) or config.get("kind") != "OVERRIDE_NOTE":
            continue
        details = config.get("details")
        if not isinstance(details, Mapping):
            continue
        for key, raw_detail in details.items():
            if not isinstance(raw_detail, Mapping):
                continue
            label_en = raw_detail.get("label_en") or raw_detail.get("label")
            label_vi = raw_detail.get("label_vi") or raw_detail.get("label") or label_en
            items_en = raw_detail.get("items_en") or raw_detail.get("items") or []
            items_vi = raw_detail.get("items_vi") or raw_detail.get("items") or items_en
            en = _join_note(label_en, items_en)
            vi = _join_note(label_vi, items_vi)
            if en or vi:
                notes.append(
                    {
                        "id": str(key),
                        "text_en": en or vi,
                        "text_vi": vi or en,
                    }
                )
    return notes


def _join_note(label, items) -> str:
    prefix = label if isinstance(label, str) else ""
    values = (
        [item for item in items if isinstance(item, str)]
        if isinstance(items, (list, tuple))
        else []
    )
    if prefix and values:
        return f"{prefix}: {', '.join(values)}"
    return prefix or ", ".join(values)
