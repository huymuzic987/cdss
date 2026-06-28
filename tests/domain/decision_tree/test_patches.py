"""Pure unit tests for context-patch execution."""

from typing import Any, cast

import pytest

from cdss.domain.decision_tree import ContextPatchError, RunState, apply_context_patch


def test_static_patch_deep_merges_nested_objects() -> None:
    state = RunState.initialize({})
    state.context.update(
        {
            "diagnosis": {"source": "existing"},
            "untouched": {"value": True},
        }
    )

    result = apply_context_patch(
        {
            "diagnosis": {"hypertension_class": "NORMAL_BP"},
            "treatment": {"follow_up": {"interval_months": 6}},
        },
        state,
    )

    assert state.context == {
        "diagnosis": {
            "source": "existing",
            "hypertension_class": "NORMAL_BP",
        },
        "untouched": {"value": True},
        "treatment": {"follow_up": {"interval_months": 6}},
    }
    assert result.changed_context_paths == [
        "context.diagnosis.hypertension_class",
        "context.treatment.follow_up.interval_months",
    ]


def test_static_patch_records_valid_overwrite() -> None:
    state = RunState.initialize({})
    state.context["risk"] = {"level": "low"}

    result = apply_context_patch({"risk": {"level": "high"}}, state)

    assert state.context["risk"] == {"level": "high"}
    assert result.changed_context_paths == ["context.risk.level"]


def test_static_patch_runs_before_ordered_operations() -> None:
    state = RunState.initialize({"active_bp_target": {"sbp": {"upper_exclusive_mmhg": 140}}})

    result = apply_context_patch(
        {
            "treatment": {"follow_up_mode": "medication"},
            "operations": [
                {
                    "op": "COPY_PATH",
                    "from_path": "input.active_bp_target",
                    "to_path": "context.treatment.bp_target",
                    "required": True,
                }
            ],
        },
        state,
    )

    assert state.context == {
        "treatment": {
            "follow_up_mode": "medication",
            "bp_target": {"sbp": {"upper_exclusive_mmhg": 140}},
        }
    }
    assert result.changed_context_paths == [
        "context.treatment.follow_up_mode",
        "context.treatment.bp_target",
    ]


def test_required_copy_path_succeeds_and_records_overwrite() -> None:
    state = RunState.initialize({"target": {"sbp": 135}})
    state.context["treatment"] = {"bp_target": {"sbp": 140}}

    result = apply_context_patch(
        {
            "operations": [
                {
                    "op": "COPY_PATH",
                    "from_path": "input.target",
                    "to_path": "context.treatment.bp_target",
                    "required": True,
                }
            ]
        },
        state,
    )

    assert state.context["treatment"] == {"bp_target": {"sbp": 135}}
    assert result.changed_context_paths == ["context.treatment.bp_target"]


def test_required_copy_path_missing_value_raises_context_patch_error() -> None:
    state = RunState.initialize({})

    with pytest.raises(ContextPatchError) as exc_info:
        apply_context_patch(
            {
                "operations": [
                    {
                        "op": "COPY_PATH",
                        "from_path": "input.active_bp_target",
                        "to_path": "context.treatment.bp_target",
                        "required": True,
                    }
                ]
            },
            state,
            tree_key="tree-3",
            node_key="restore-target",
        )

    assert exc_info.value.tree_key == "tree-3"
    assert exc_info.value.node_key == "restore-target"
    assert exc_info.value.details["reason"] == "required_copy_source_missing"
    assert exc_info.value.partial_run_state is not None
    assert exc_info.value.partial_run_state.context == {}


def test_optional_copy_path_missing_value_is_noop() -> None:
    state = RunState.initialize({})

    result = apply_context_patch(
        {
            "operations": [
                {
                    "op": "COPY_PATH",
                    "from_path": "input.missing",
                    "to_path": "context.target",
                    "required": False,
                }
            ]
        },
        state,
    )

    assert state.context == {}
    assert result.changed_context_paths == []


def test_copy_path_rejects_target_outside_context() -> None:
    state = RunState.initialize({"source": 1})

    with pytest.raises(ContextPatchError) as exc_info:
        apply_context_patch(
            {
                "operations": [
                    {
                        "op": "COPY_PATH",
                        "from_path": "input.source",
                        "to_path": "input.target",
                        "required": True,
                    }
                ]
            },
            state,
        )

    assert exc_info.value.details["reason"] == "invalid_copy_target_path"
    assert state.input_snapshot.to_dict() == {"source": 1}


def test_copy_path_source_and_target_are_deeply_isolated() -> None:
    state = RunState.initialize(
        {"active_target": {"thresholds": [130, 140]}},
    )
    state.context["source"] = {"steps": [{"dose": 1}]}

    apply_context_patch(
        {
            "operations": [
                {
                    "op": "COPY_PATH",
                    "from_path": "input.active_target",
                    "to_path": "context.from_input",
                    "required": True,
                },
                {
                    "op": "COPY_PATH",
                    "from_path": "context.source",
                    "to_path": "context.from_context",
                    "required": True,
                },
            ]
        },
        state,
    )

    from_input = cast(dict[str, Any], state.context["from_input"])
    cast(list[int], from_input["thresholds"]).append(999)
    from_context = cast(dict[str, Any], state.context["from_context"])
    copied_steps = cast(list[dict[str, int]], from_context["steps"])
    copied_steps[0]["dose"] = 2

    assert state.input_snapshot.to_dict() == {"active_target": {"thresholds": [130, 140]}}
    assert state.context["source"] == {"steps": [{"dose": 1}]}


def test_unsupported_context_operation_raises_typed_error() -> None:
    state = RunState.initialize({})

    with pytest.raises(ContextPatchError) as exc_info:
        apply_context_patch(
            {"operations": [{"op": "DELETE_PATH"}]},
            state,
        )

    assert exc_info.value.details["reason"] == "unsupported_context_operation"
