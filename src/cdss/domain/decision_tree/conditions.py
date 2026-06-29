"""Pure evaluator for the frozen decision-tree condition dialect."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import Field

from cdss.domain.decision_tree.contracts import (
    JsonObject,
    NodeType,
    RunState,
    RuntimeModel,
    copy_json_value,
)
from cdss.domain.decision_tree.errors import (
    InvalidConditionDefinition,
    InvalidRuntimeValueType,
    MissingRuntimePath,
    UnsupportedOperator,
)
from cdss.domain.decision_tree.paths import resolve_runtime_path

_LOGICAL_FORMS = frozenset({"all", "any", "not"})
_SUPPORTED_OPERATORS = frozenset({"eq", "exists", "in", "lt", "lte", "gt", "gte"})


class ConditionEvaluation(RuntimeModel):
    result: bool
    details: JsonObject = Field(default_factory=dict)


def evaluate_condition(
    condition_definition: Mapping[str, Any] | None,
    run_state: RunState,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
) -> ConditionEvaluation:
    """Evaluate one non-null condition definition without mutating runtime state."""

    validate_condition_definition(
        condition_definition,
        tree_key=tree_key,
        node_key=node_key,
        partial_run_state=run_state,
    )
    evaluator = _ConditionEvaluator(run_state, tree_key=tree_key, node_key=node_key)
    return evaluator.evaluate(condition_definition)


def validate_condition_definition(
    condition_definition: Mapping[str, Any] | None,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
    partial_run_state: RunState | None = None,
) -> None:
    """Validate condition grammar and runtime path syntax without resolving values."""

    validator = _ConditionDefinitionValidator(
        tree_key=tree_key,
        node_key=node_key,
        partial_run_state=partial_run_state,
    )
    validator.validate(condition_definition)


def evaluate_candidate_condition(
    node_type: NodeType,
    condition_definition: Mapping[str, Any] | None,
    run_state: RunState,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
) -> ConditionEvaluation:
    """Evaluate a candidate node, including the unconditional-node rule."""

    if condition_definition is None:
        if node_type is NodeType.CONDITION:
            raise InvalidConditionDefinition(
                tree_key=tree_key,
                node_key=node_key,
                details={"reason": "condition_node_has_null_definition"},
                partial_run_state=run_state,
            )
        return ConditionEvaluation(
            result=True,
            details={"kind": "unconditional", "result": True},
        )

    return evaluate_condition(
        condition_definition,
        run_state,
        tree_key=tree_key,
        node_key=node_key,
    )


@dataclass(frozen=True, slots=True)
class _ConditionEvaluator:
    run_state: RunState
    tree_key: str | None
    node_key: str | None

    def evaluate(self, expression: Mapping[str, Any] | None) -> ConditionEvaluation:
        if expression is None:
            raise self._invalid("null_condition_definition")
        if not isinstance(expression, Mapping):
            raise self._invalid("condition_must_be_object")

        logical_forms = _LOGICAL_FORMS.intersection(expression)
        if logical_forms:
            if len(logical_forms) != 1 or len(expression) != 1:
                raise self._invalid("logical_form_must_be_exclusive")
            form = next(iter(logical_forms))
            if form == "not":
                return self._evaluate_not(expression[form])
            return self._evaluate_group(form, expression[form])

        return self._evaluate_comparison(expression)

    def _evaluate_group(self, form: str, children_value: Any) -> ConditionEvaluation:
        if not isinstance(children_value, (list, tuple)) or not children_value:
            raise self._invalid(f"{form}_must_be_non_empty_array")

        children = [self.evaluate(child) for child in children_value]
        result = (
            all(child.result for child in children)
            if form == "all"
            else any(child.result for child in children)
        )
        return ConditionEvaluation(
            result=result,
            details={
                "kind": form,
                "result": result,
                "children": [child.details for child in children],
            },
        )

    def _evaluate_not(self, child_value: Any) -> ConditionEvaluation:
        if not isinstance(child_value, Mapping):
            raise self._invalid("not_must_contain_condition_object")
        child = self.evaluate(child_value)
        result = not child.result
        return ConditionEvaluation(
            result=result,
            details={"kind": "not", "result": result, "child": child.details},
        )

    def _evaluate_comparison(self, expression: Mapping[str, Any]) -> ConditionEvaluation:
        operator = expression.get("op")
        if not isinstance(operator, str):
            raise self._invalid("comparison_requires_string_operator")
        if operator not in _SUPPORTED_OPERATORS:
            raise UnsupportedOperator(
                tree_key=self.tree_key,
                node_key=self.node_key,
                details={"operator": operator},
                partial_run_state=self.run_state,
            )

        if operator == "exists":
            path = expression.get("path")
            if not isinstance(path, str):
                raise self._invalid("exists_path_must_be_string")
            try:
                value = resolve_runtime_path(
                    self.run_state,
                    path,
                    tree_key=self.tree_key,
                    node_key=self.node_key,
                )
            except MissingRuntimePath:
                return ConditionEvaluation(
                    result=False,
                    details={
                        "kind": "existence",
                        "operator": operator,
                        "path": path,
                        "result": False,
                    },
                )
            return ConditionEvaluation(
                result=True,
                details={
                    "kind": "existence",
                    "operator": operator,
                    "path": path,
                    "value": copy_json_value(value),
                    "result": True,
                },
            )

        left_forms = [key for key in ("path", "left") if key in expression]
        right_forms = [key for key in ("value", "value_from_path") if key in expression]
        if len(left_forms) != 1 or len(right_forms) != 1:
            raise self._invalid("comparison_requires_one_left_and_one_right_operand")

        expected_keys = {"op", left_forms[0], right_forms[0]}
        if set(expression) != expected_keys:
            raise self._invalid("comparison_contains_unknown_or_conflicting_keys")

        if left_forms[0] == "path":
            left, left_details = self._resolve_path_operand(expression["path"], "left")
        else:
            left, left_details = self._evaluate_left_expression(expression["left"])

        if right_forms[0] == "value_from_path":
            right, right_details = self._resolve_path_operand(
                expression["value_from_path"], "right"
            )
        else:
            try:
                right = copy_json_value(expression["value"])
            except TypeError as exc:
                raise self._invalid("comparison_literal_is_not_json") from exc
            right_details = {"kind": "literal", "value": right}

        result = self._apply_operator(operator, left, right)
        return ConditionEvaluation(
            result=result,
            details={
                "kind": "comparison",
                "operator": operator,
                "left": left_details,
                "right": right_details,
                "result": result,
            },
        )

    def _resolve_path_operand(self, path_value: Any, operand: str) -> tuple[Any, JsonObject]:
        if not isinstance(path_value, str):
            raise self._invalid(f"{operand}_path_must_be_string")
        value = resolve_runtime_path(
            self.run_state,
            path_value,
            tree_key=self.tree_key,
            node_key=self.node_key,
        )
        try:
            json_value = copy_json_value(value)
        except TypeError as exc:
            raise self._invalid("resolved_value_is_not_json") from exc
        return json_value, {"kind": "path", "path": path_value, "value": json_value}

    def _evaluate_left_expression(self, left_value: Any) -> tuple[int | float, JsonObject]:
        if not isinstance(left_value, Mapping):
            raise self._invalid("left_expression_must_be_object")
        if set(left_value) != {"expression", "left_path", "right_path"}:
            raise self._invalid("subtract_expression_has_invalid_shape")
        if left_value["expression"] != "subtract":
            raise self._invalid("unsupported_left_expression")

        left_path = left_value["left_path"]
        right_path = left_value["right_path"]
        if not isinstance(left_path, str) or not isinstance(right_path, str):
            raise self._invalid("subtract_paths_must_be_strings")

        left_operand = resolve_runtime_path(
            self.run_state,
            left_path,
            tree_key=self.tree_key,
            node_key=self.node_key,
        )
        right_operand = resolve_runtime_path(
            self.run_state,
            right_path,
            tree_key=self.tree_key,
            node_key=self.node_key,
        )
        self._require_numeric(left_operand, operator="subtract", operand="left")
        self._require_numeric(right_operand, operator="subtract", operand="right")
        result = left_operand - right_operand
        return result, {
            "kind": "subtract",
            "left_path": left_path,
            "left_value": left_operand,
            "right_path": right_path,
            "right_value": right_operand,
            "value": result,
        }

    def _apply_operator(self, operator: str, left: Any, right: Any) -> bool:
        if operator == "eq":
            return _strict_equal(left, right)
        if operator == "in":
            if not isinstance(right, list):
                raise InvalidRuntimeValueType(
                    tree_key=self.tree_key,
                    node_key=self.node_key,
                    details={
                        "operator": operator,
                        "operand": "right",
                        "actual_type": type(right).__name__,
                    },
                    partial_run_state=self.run_state,
                )
            return any(_strict_equal(left, item) for item in right)

        self._require_numeric(left, operator=operator, operand="left")
        self._require_numeric(right, operator=operator, operand="right")
        if operator == "lt":
            return left < right
        if operator == "lte":
            return left <= right
        if operator == "gt":
            return left > right
        return left >= right

    def _require_numeric(self, value: Any, *, operator: str, operand: str) -> None:
        if type(value) not in {int, float}:
            raise InvalidRuntimeValueType(
                tree_key=self.tree_key,
                node_key=self.node_key,
                details={
                    "operator": operator,
                    "operand": operand,
                    "actual_type": type(value).__name__,
                },
                partial_run_state=self.run_state,
            )

    def _invalid(self, reason: str) -> InvalidConditionDefinition:
        return InvalidConditionDefinition(
            tree_key=self.tree_key,
            node_key=self.node_key,
            details={"reason": reason},
            partial_run_state=self.run_state,
        )


@dataclass(frozen=True, slots=True)
class _ConditionDefinitionValidator:
    tree_key: str | None
    node_key: str | None
    partial_run_state: RunState | None

    def validate(self, expression: Mapping[str, Any] | None) -> None:
        if expression is None:
            raise self._invalid("null_condition_definition")
        if not isinstance(expression, Mapping):
            raise self._invalid("condition_must_be_object")

        logical_forms = _LOGICAL_FORMS.intersection(expression)
        if logical_forms:
            if len(logical_forms) != 1 or len(expression) != 1:
                raise self._invalid("logical_form_must_be_exclusive")
            form = next(iter(logical_forms))
            value = expression[form]
            if form == "not":
                if not isinstance(value, Mapping):
                    raise self._invalid("not_must_contain_condition_object")
                self.validate(value)
                return
            if not isinstance(value, (list, tuple)) or not value:
                raise self._invalid(f"{form}_must_be_non_empty_array")
            for child in value:
                self.validate(child)
            return

        self._validate_comparison(expression)

    def _validate_comparison(self, expression: Mapping[str, Any]) -> None:
        operator = expression.get("op")
        if not isinstance(operator, str):
            raise self._invalid("comparison_requires_string_operator")
        if operator not in _SUPPORTED_OPERATORS:
            raise UnsupportedOperator(
                tree_key=self.tree_key,
                node_key=self.node_key,
                details={"operator": operator},
                partial_run_state=self.partial_run_state,
            )

        if operator == "exists":
            if set(expression) != {"op", "path"}:
                raise self._invalid("exists_requires_only_path")
            self._validate_path(expression["path"], "exists_path")
            return

        left_forms = [key for key in ("path", "left") if key in expression]
        right_forms = [key for key in ("value", "value_from_path") if key in expression]
        if len(left_forms) != 1 or len(right_forms) != 1:
            raise self._invalid("comparison_requires_one_left_and_one_right_operand")
        if set(expression) != {"op", left_forms[0], right_forms[0]}:
            raise self._invalid("comparison_contains_unknown_or_conflicting_keys")

        if left_forms[0] == "path":
            self._validate_path(expression["path"], "left_path")
        else:
            self._validate_left_expression(expression["left"])

        if right_forms[0] == "value_from_path":
            if operator == "in":
                raise self._invalid("in_requires_literal_array")
            self._validate_path(expression["value_from_path"], "value_from_path")
        else:
            try:
                literal = copy_json_value(expression["value"])
            except TypeError as exc:
                raise self._invalid("comparison_literal_is_not_json") from exc
            if operator == "in" and not isinstance(literal, list):
                raise self._invalid("in_requires_literal_array")
            if operator not in {"eq", "in"} and type(literal) not in {int, float}:
                raise self._invalid("numeric_operator_requires_numeric_literal")

    def _validate_left_expression(self, left_value: Any) -> None:
        if not isinstance(left_value, Mapping):
            raise self._invalid("left_expression_must_be_object")
        if set(left_value) != {"expression", "left_path", "right_path"}:
            raise self._invalid("subtract_expression_has_invalid_shape")
        if left_value["expression"] != "subtract":
            raise self._invalid("unsupported_left_expression")
        self._validate_path(left_value["left_path"], "subtract_left_path")
        self._validate_path(left_value["right_path"], "subtract_right_path")

    def _validate_path(self, path: Any, role: str) -> None:
        if not isinstance(path, str):
            raise self._invalid(f"{role}_must_be_string")
        parts = path.split(".")
        if (
            len(parts) < 2
            or parts[0] not in {"input", "context"}
            or any(not part for part in parts)
        ):
            raise self._invalid(f"invalid_{role}")

    def _invalid(self, reason: str) -> InvalidConditionDefinition:
        return InvalidConditionDefinition(
            tree_key=self.tree_key,
            node_key=self.node_key,
            details={"reason": reason},
            partial_run_state=self.partial_run_state,
        )


def _strict_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if type(left) in {int, float} and type(right) in {int, float}:
        return left == right
    return type(left) is type(right) and left == right
