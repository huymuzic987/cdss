"""Pure unit tests for decision-tree runtime contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cdss.domain.decision_tree import RunState, TraversalResult


def test_run_state_deep_copies_and_freezes_input_snapshot() -> None:
    runtime_input = {
        "measurements": {"clinic": [140, 90]},
        "flags": [True, False],
    }

    state = RunState.initialize(runtime_input)
    runtime_input["measurements"]["clinic"][0] = 999
    runtime_input["flags"].append(True)

    assert state.model_dump(mode="json")["input_snapshot"] == {
        "measurements": {"clinic": [140, 90]},
        "flags": [True, False],
    }
    with pytest.raises(TypeError):
        state.input_snapshot["new"] = "value"  # type: ignore[index]
    with pytest.raises(AttributeError):
        state.input_snapshot["flags"].append(True)
    with pytest.raises(ValidationError):
        state.input_snapshot = {}  # type: ignore[assignment]


def test_successful_empty_result_is_json_serializable() -> None:
    state = RunState.initialize({})
    started_at = datetime(2026, 6, 28, 8, 0, tzinfo=UTC)
    completed_at = datetime(2026, 6, 28, 8, 0, 1, tzinfo=UTC)

    result = TraversalResult.from_run_state(
        state,
        tree_metadata=[],
        started_at=started_at,
        completed_at=completed_at,
    )

    assert result.model_dump(mode="json") == {
        "status": "success",
        "input_snapshot": {},
        "context": {},
        "actions": [],
        "trace": [],
        "references": [],
        "tree_metadata": [],
        "started_at": "2026-06-28T08:00:00Z",
        "completed_at": "2026-06-28T08:00:01Z",
    }
    assert result.model_dump_json()
