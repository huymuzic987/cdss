"""Pure unit tests for action collection."""

from typing import Any, cast
from uuid import UUID

import pytest

from cdss.domain.decision_tree import (
    InvalidTreeStructure,
    NodeDefinition,
    NodeType,
    RunState,
    collect_action,
)


def _node(
    node_type: NodeType,
    *,
    action_payload: dict[str, Any] | None,
) -> NodeDefinition:
    return NodeDefinition(
        id=UUID(int=1),
        tree_id=UUID(int=2),
        node_key="recommendation",
        node_type=node_type,
        text_en="Continue monitoring",
        text_vi="Tiep tuc theo doi",
        action_payload=action_payload,
    )


def test_collects_deep_copied_action_with_source_metadata() -> None:
    payload = {"kind": "monitor", "schedule": {"months": [3, 6]}}
    node = _node(NodeType.ACTION, action_payload=payload)
    state = RunState.initialize({})

    action = collect_action(node, state, tree_key="treatment-tree")
    payload["kind"] = "changed"
    cast(list[int], cast(dict[str, Any], payload["schedule"])["months"]).append(12)

    assert action is not None
    assert action.model_dump(mode="json") == {
        "tree_key": "treatment-tree",
        "node_key": "recommendation",
        "node_type": "ACTION",
        "text_en": "Continue monitoring",
        "text_vi": "Tiep tuc theo doi",
        "payload": {
            "kind": "monitor",
            "schedule": {"months": [3, 6]},
        },
    }
    assert state.actions == [action]


def test_end_node_can_emit_action_payload() -> None:
    node = _node(NodeType.END, action_payload={"status": "maintain"})
    state = RunState.initialize({})

    action = collect_action(node, state, tree_key="treatment-tree")

    assert action is not None
    assert action.node_type is NodeType.END
    assert action.payload == {"status": "maintain"}


def test_node_without_action_payload_does_not_append_action() -> None:
    node = _node(NodeType.ACTION, action_payload=None)
    state = RunState.initialize({})

    action = collect_action(node, state, tree_key="treatment-tree")

    assert action is None
    assert state.actions == []


def test_non_action_node_with_payload_is_invalid_structure() -> None:
    node = _node(NodeType.INFERENCE, action_payload={"invalid": True})
    state = RunState.initialize({})

    with pytest.raises(InvalidTreeStructure):
        collect_action(node, state, tree_key="treatment-tree")


def test_start_combination_end_node_attaches_medicine_options_from_context() -> None:
    node = _node(
        NodeType.END,
        action_payload={"action_type": "INITIAL_TWO_DRUG_COMBINATION"},
    )
    state = RunState.initialize({})
    state.context["treatment_preferences"] = {
        "combination_options": [["A", "C"], ["A", "D"]],
    }

    action = collect_action(node, state, tree_key="drug-combination")

    assert action is not None
    medicine_options = cast(list[dict[str, Any]], action.payload["medicine_options"])
    assert [o["classes"] for o in medicine_options] == [["A", "C"], ["A", "D"]]
    first_medicines = cast(dict[str, Any], medicine_options[0]["medicines"])
    assert "Losartan" in {m["name"] for m in first_medicines["A"]}


def test_maintain_regimen_end_node_does_not_attach_medicine_options() -> None:
    node = _node(
        NodeType.END,
        action_payload={"action_type": "MAINTAIN_CURRENT_REGIMEN"},
    )
    state = RunState.initialize({})
    # Simulates a leftover advisory value from an earlier comorbidity tree --
    # this END node isn't starting anything, so it must not be expanded.
    state.context["treatment_preferences"] = {
        "combination_options": [["A", "C"], ["A", "D"]],
    }

    action = collect_action(node, state, tree_key="essential-treatment-strategy")

    assert action is not None
    assert action.payload == {"action_type": "MAINTAIN_CURRENT_REGIMEN"}


def test_start_combination_action_node_does_not_attach_medicine_options() -> None:
    # Only END nodes are in scope, even if the action_type matches.
    node = _node(
        NodeType.ACTION,
        action_payload={"action_type": "INITIAL_TWO_DRUG_COMBINATION"},
    )
    state = RunState.initialize({})
    state.context["treatment_preferences"] = {"combination_options": [["A", "C"]]}

    action = collect_action(node, state, tree_key="drug-combination")

    assert action is not None
    assert action.payload == {"action_type": "INITIAL_TWO_DRUG_COMBINATION"}


def test_start_combination_end_node_without_context_leaves_payload_unchanged() -> None:
    node = _node(
        NodeType.END,
        action_payload={"action_type": "CONSIDER_MONOTHERAPY"},
    )
    state = RunState.initialize({})

    action = collect_action(node, state, tree_key="drug-combination")

    assert action is not None
    assert action.payload == {"action_type": "CONSIDER_MONOTHERAPY"}


def test_single_drug_end_node_attaches_the_named_drug() -> None:
    node = _node(
        NodeType.END,
        action_payload={
            "action_type": "ASPIRIN_PROPHYLAXIS",
            "follow_up_mode": "NEW_ENCOUNTER",
        },
    )
    state = RunState.initialize({})

    action = collect_action(node, state, tree_key="hypertension-in-pregnancy")

    assert action is not None
    medicines = cast(list[dict[str, Any]], action.payload["medicines"])
    assert [m["name"] for m in medicines] == ["Aspirin"]
    assert medicines[0]["dose_low"] == "75 - 81 mg/ngày"
    # Unrelated fields, and the fact this isn't a combination action_type,
    # are left untouched.
    assert action.payload["follow_up_mode"] == "NEW_ENCOUNTER"
    assert "medicine_options" not in action.payload


def test_single_drug_action_node_does_not_attach_medicines() -> None:
    # Both drug-reference mechanisms are END-only, matching where the real
    # T12_END_ASPIRIN_PROPHYLAXIS node lives.
    node = _node(
        NodeType.ACTION,
        action_payload={"action_type": "ASPIRIN_PROPHYLAXIS"},
    )
    state = RunState.initialize({})

    action = collect_action(node, state, tree_key="hypertension-in-pregnancy")

    assert action is not None
    assert action.payload == {"action_type": "ASPIRIN_PROPHYLAXIS"}
