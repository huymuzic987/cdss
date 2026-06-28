"""Pure unit tests for strict runtime path resolution."""

import pytest

from cdss.domain.decision_tree import MissingRuntimePath, RunState, resolve_runtime_path


def test_resolves_input_and_context_paths() -> None:
    state = RunState.initialize(
        {"clinic": {"current": {"sbp": 138}}, "is_medication_follow_up": True}
    )
    state.context["risk"] = {"level": "high"}

    assert resolve_runtime_path(state, "input.clinic.current.sbp") == 138
    assert resolve_runtime_path(state, "input.is_medication_follow_up") is True
    assert resolve_runtime_path(state, "context.risk.level") == "high"


def test_missing_path_raises_typed_error() -> None:
    state = RunState.initialize({"clinic": {}})

    with pytest.raises(MissingRuntimePath) as exc_info:
        resolve_runtime_path(
            state,
            "input.clinic.sbp",
            tree_key="tree-1",
            node_key="condition-1",
        )

    assert exc_info.value.tree_key == "tree-1"
    assert exc_info.value.node_key == "condition-1"
    assert exc_info.value.details == {
        "path": "input.clinic.sbp",
        "reason": "missing_path_segment",
        "resolved_prefix": "input.clinic",
        "missing_segment": "sbp",
    }


@pytest.mark.parametrize(
    "path",
    [
        "patient.age",
        "runtime.value",
        "input",
        "context.",
        "input..sbp",
    ],
)
def test_rejects_paths_outside_strict_runtime_syntax(path: str) -> None:
    state = RunState.initialize({})

    with pytest.raises(MissingRuntimePath):
        resolve_runtime_path(state, path)


def test_rejects_traversal_through_non_object_value() -> None:
    state = RunState.initialize({"measurements": [120, 80]})

    with pytest.raises(MissingRuntimePath) as exc_info:
        resolve_runtime_path(state, "input.measurements.sbp")

    assert exc_info.value.details["reason"] == "non_object_path_segment"
