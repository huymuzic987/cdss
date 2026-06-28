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
