"""Pure unit tests for the frozen condition JSON dialect."""

import json
from copy import deepcopy
from typing import Any, cast

import pytest

from cdss.domain.decision_tree import (
    InvalidConditionDefinition,
    InvalidRuntimeValueType,
    MissingRuntimePath,
    NodeType,
    RunState,
    UnsupportedOperator,
    evaluate_candidate_condition,
    evaluate_condition,
)


def _state(runtime_input: dict[str, Any], context: dict[str, Any] | None = None) -> RunState:
    state = RunState.initialize(runtime_input)
    if context is not None:
        state.context.update(deepcopy(context))
    return state


@pytest.mark.parametrize(
    ("operator", "left", "right", "expected"),
    [
        ("eq", 140, 140, True),
        ("lt", 139, 140, True),
        ("lte", 140, 140, True),
        ("gt", 141, 140, True),
        ("gte", 140, 140, True),
        ("lt", 141, 140, False),
    ],
)
def test_evaluates_all_supported_operators(
    operator: str, left: int, right: int, expected: bool
) -> None:
    state = _state({"actual": left})

    evaluation = evaluate_condition(
        {"path": "input.actual", "op": operator, "value": right},
        state,
    )

    assert evaluation.result is expected
    assert evaluation.details["operator"] == operator
    assert evaluation.details["result"] is expected


@pytest.mark.parametrize(("runtime_input", "expected"), [({"value": None}, True), ({}, False)])
def test_exists_checks_path_presence_without_hiding_other_missing_paths(
    runtime_input: dict[str, Any], expected: bool
) -> None:
    evaluation = evaluate_condition(
        {"path": "input.value", "op": "exists"},
        _state(runtime_input),
    )

    assert evaluation.result is expected
    assert evaluation.details["kind"] == "existence"


@pytest.mark.parametrize(
    ("runtime_value", "expected"),
    [(1, True), (2, True), (3, False), (True, False)],
)
def test_in_uses_strict_membership(runtime_value: Any, expected: bool) -> None:
    evaluation = evaluate_condition(
        {"path": "input.value", "op": "in", "value": [1, 2]},
        _state({"value": runtime_value}),
    )

    assert evaluation.result is expected


@pytest.mark.parametrize(
    ("runtime_value", "static_value"),
    [
        (True, True),
        ("high", "high"),
        ([1, 2], [1, 2]),
        ({"upper": 140}, {"upper": 140}),
    ],
)
def test_eq_supports_static_json_values(runtime_value: Any, static_value: Any) -> None:
    state = _state({"actual": runtime_value})

    evaluation = evaluate_condition(
        {"path": "input.actual", "op": "eq", "value": static_value},
        state,
    )

    assert evaluation.result is True


def test_nested_all_any_not_returns_ordered_details() -> None:
    state = _state({"sbp": 138, "dbp": 86, "has_red_flag": False})
    definition = {
        "all": [
            {
                "any": [
                    {"path": "input.sbp", "op": "lt", "value": 130},
                    {"path": "input.dbp", "op": "lt", "value": 90},
                ]
            },
            {
                "not": {
                    "path": "input.has_red_flag",
                    "op": "eq",
                    "value": True,
                }
            },
        ]
    }

    evaluation = evaluate_condition(definition, state)

    assert evaluation.result is True
    assert evaluation.details["kind"] == "all"
    children = cast(list[dict[str, Any]], evaluation.details["children"])
    assert children[0]["kind"] == "any"
    any_children = cast(list[dict[str, Any]], children[0]["children"])
    assert [child["result"] for child in any_children] == [False, True]
    assert children[1]["kind"] == "not"
    not_child = cast(dict[str, Any], children[1]["child"])
    assert not_child["result"] is False
    assert json.loads(evaluation.model_dump_json())["result"] is True


def test_resolves_dynamic_value_from_path() -> None:
    state = _state(
        {"current_sbp": 134},
        {"treatment": {"bp_target": {"sbp": {"upper_exclusive_mmhg": 140}}}},
    )

    evaluation = evaluate_condition(
        {
            "path": "input.current_sbp",
            "op": "lt",
            "value_from_path": ("context.treatment.bp_target.sbp.upper_exclusive_mmhg"),
        },
        state,
    )

    assert evaluation.result is True
    assert evaluation.details["right"] == {
        "kind": "path",
        "path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg",
        "value": 140,
    }


def test_evaluates_subtraction_expression() -> None:
    state = _state({"previous_sbp": 150, "current_sbp": 138})

    evaluation = evaluate_condition(
        {
            "left": {
                "expression": "subtract",
                "left_path": "input.previous_sbp",
                "right_path": "input.current_sbp",
            },
            "op": "gte",
            "value": 10,
        },
        state,
    )

    assert evaluation.result is True
    assert evaluation.details["left"] == {
        "kind": "subtract",
        "left_path": "input.previous_sbp",
        "left_value": 150,
        "right_path": "input.current_sbp",
        "right_value": 138,
        "value": 12,
    }


def test_missing_runtime_path_is_not_treated_as_false() -> None:
    state = _state({})

    with pytest.raises(MissingRuntimePath):
        evaluate_condition(
            {"path": "input.current_sbp", "op": "gte", "value": 140},
            state,
        )


def test_logical_groups_do_not_hide_missing_paths_by_short_circuiting() -> None:
    state = _state({"known": True})
    definition = {
        "any": [
            {"path": "input.known", "op": "eq", "value": True},
            {"path": "input.missing", "op": "eq", "value": True},
        ]
    }

    with pytest.raises(MissingRuntimePath):
        evaluate_condition(definition, state)


def test_numeric_string_is_not_coerced_for_numeric_comparison() -> None:
    state = _state({"current_sbp": "140"})

    with pytest.raises(InvalidRuntimeValueType) as exc_info:
        evaluate_condition(
            {"path": "input.current_sbp", "op": "gte", "value": 140},
            state,
        )

    assert exc_info.value.details["actual_type"] == "str"


def test_eq_does_not_coerce_string_to_number() -> None:
    state = _state({"current_sbp": "140"})

    evaluation = evaluate_condition(
        {"path": "input.current_sbp", "op": "eq", "value": 140},
        state,
    )

    assert evaluation.result is False


def test_boolean_is_not_a_numeric_operand() -> None:
    state = _state({"current_sbp": True})

    with pytest.raises(InvalidRuntimeValueType) as exc_info:
        evaluate_condition(
            {"path": "input.current_sbp", "op": "gte", "value": 1},
            state,
        )

    assert exc_info.value.details["actual_type"] == "bool"


def test_subtraction_requires_numeric_operands() -> None:
    state = _state({"previous_sbp": 150, "current_sbp": False})

    with pytest.raises(InvalidRuntimeValueType) as exc_info:
        evaluate_condition(
            {
                "left": {
                    "expression": "subtract",
                    "left_path": "input.previous_sbp",
                    "right_path": "input.current_sbp",
                },
                "op": "gte",
                "value": 10,
            },
            state,
        )

    assert exc_info.value.details["operator"] == "subtract"
    assert exc_info.value.details["operand"] == "right"


def test_unsupported_operator_raises_typed_error() -> None:
    state = _state({"actual": 1})

    with pytest.raises(UnsupportedOperator) as exc_info:
        evaluate_condition(
            {"path": "input.actual", "op": "neq", "value": 1},
            state,
            tree_key="tree-1",
            node_key="condition-1",
        )

    assert exc_info.value.details == {"operator": "neq"}
    assert exc_info.value.tree_key == "tree-1"
    assert exc_info.value.node_key == "condition-1"


@pytest.mark.parametrize(
    "definition",
    [
        {},
        {"all": []},
        {"any": "not-an-array"},
        {"not": []},
        {
            "all": [{"path": "input.actual", "op": "eq", "value": 1}],
            "any": [{"path": "input.actual", "op": "eq", "value": 1}],
        },
        {"path": "input.actual", "op": "eq"},
        {
            "path": "input.actual",
            "left": {
                "expression": "subtract",
                "left_path": "input.a",
                "right_path": "input.b",
            },
            "op": "eq",
            "value": 1,
        },
        {"path": "input.actual", "op": "eq", "value": 1, "extra": True},
        {"path": "input.actual", "op": "exists", "value": 1},
        {"path": "input.actual", "op": "in", "value": "not-an-array"},
        {
            "left": {
                "expression": "add",
                "left_path": "input.a",
                "right_path": "input.b",
            },
            "op": "eq",
            "value": 1,
        },
    ],
)
def test_rejects_malformed_condition_json(definition: dict[str, Any]) -> None:
    state = _state({"actual": 1, "a": 2, "b": 1})

    with pytest.raises(InvalidConditionDefinition):
        evaluate_condition(definition, state)


def test_null_condition_definition_is_invalid() -> None:
    state = _state({})

    with pytest.raises(InvalidConditionDefinition):
        evaluate_condition(None, state)


def test_condition_node_requires_definition() -> None:
    state = _state({})

    with pytest.raises(InvalidConditionDefinition):
        evaluate_candidate_condition(NodeType.CONDITION, None, state)


@pytest.mark.parametrize("node_type", [NodeType.START, NodeType.ACTION, NodeType.END])
def test_non_condition_node_without_definition_is_unconditional(node_type: NodeType) -> None:
    state = _state({})

    evaluation = evaluate_candidate_condition(node_type, None, state)

    assert evaluation.result is True
    assert evaluation.details == {"kind": "unconditional", "result": True}


def test_non_condition_node_with_definition_is_a_conditional_candidate() -> None:
    state = _state({"actual": 1})

    evaluation = evaluate_candidate_condition(
        NodeType.LINK,
        {"path": "input.actual", "op": "eq", "value": 1},
        state,
    )

    assert evaluation.result is True


def test_evaluation_does_not_mutate_input_context_or_definition() -> None:
    runtime_input = {"previous_sbp": 150, "current_sbp": 138, "flags": [True]}
    context = {"target": {"reduction": 10}}
    definition = {
        "all": [
            {
                "left": {
                    "expression": "subtract",
                    "left_path": "input.previous_sbp",
                    "right_path": "input.current_sbp",
                },
                "op": "gte",
                "value_from_path": "context.target.reduction",
            },
            {"path": "input.flags", "op": "eq", "value": [True]},
        ]
    }
    state = _state(runtime_input, context)
    state_before = state.model_dump(mode="json")
    definition_before = deepcopy(definition)

    evaluation = evaluate_condition(definition, state)

    assert evaluation.result is True
    assert state.model_dump(mode="json") == state_before
    assert runtime_input == {"previous_sbp": 150, "current_sbp": 138, "flags": [True]}
    assert definition == definition_before
