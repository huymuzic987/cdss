"""Pure unit tests for typed decision-tree errors."""

import json

import pytest

from cdss.domain.decision_tree import (
    ContextPatchError,
    DecisionTreeError,
    InvalidConditionDefinition,
    InvalidRuntimeValueType,
    InvalidStartNode,
    InvalidTreeStructure,
    LinkNotEnabled,
    LinkTargetNodeNotFound,
    LinkTargetNotFound,
    MissingRuntimePath,
    NoMatchingTransition,
    RunState,
    TraversalCycleDetected,
    TraversalLimitExceeded,
    TreeNotFound,
    UnsupportedOperator,
)

ERROR_TYPES = [
    (TreeNotFound, "tree_not_found"),
    (InvalidTreeStructure, "invalid_tree_structure"),
    (InvalidStartNode, "invalid_start_node"),
    (InvalidConditionDefinition, "invalid_condition_definition"),
    (UnsupportedOperator, "unsupported_operator"),
    (MissingRuntimePath, "missing_runtime_path"),
    (InvalidRuntimeValueType, "invalid_runtime_value_type"),
    (ContextPatchError, "context_patch_error"),
    (NoMatchingTransition, "no_matching_transition"),
    (LinkTargetNotFound, "link_target_not_found"),
    (LinkTargetNodeNotFound, "link_target_node_not_found"),
    (TraversalCycleDetected, "traversal_cycle_detected"),
    (TraversalLimitExceeded, "traversal_limit_exceeded"),
    (LinkNotEnabled, "link_not_enabled"),
]


@pytest.mark.parametrize(("error_type", "expected_code"), ERROR_TYPES)
def test_typed_error_is_json_serializable(
    error_type: type[DecisionTreeError], expected_code: str
) -> None:
    error = error_type(
        "test failure",
        tree_key="tree-1",
        node_key="node-1",
        details={"reason": "test"},
    )

    payload = error.to_dict()

    assert payload == {
        "code": expected_code,
        "message": "test failure",
        "tree_key": "tree-1",
        "node_key": "node-1",
        "details": {"reason": "test"},
        "partial_run_state": None,
    }
    assert json.loads(json.dumps(payload)) == payload


def test_execution_error_preserves_partial_run_state_snapshot() -> None:
    state = RunState.initialize({"patient": {"age": 52}})
    state.context["risk"] = {"level": "high"}

    error = NoMatchingTransition(
        tree_key="risk-classification",
        node_key="select-branch",
        partial_run_state=state,
    )
    state.context["risk"] = {"level": "changed-after-error"}

    partial_state = error.to_dict()["partial_run_state"]
    assert partial_state is not None
    assert partial_state["input_snapshot"] == {"patient": {"age": 52}}
    assert partial_state["context"] == {"risk": {"level": "high"}}
    assert partial_state["actions"] == []
    assert partial_state["trace"] == []
    assert partial_state["references"] == []
