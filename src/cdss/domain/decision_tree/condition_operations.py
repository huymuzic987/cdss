"""Runtime operand resolution and comparison operators."""

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.contracts import JsonObject, RunState, copy_json_value
from cdss.domain.decision_tree.errors import InvalidConditionDefinition, InvalidRuntimeValueType
from cdss.domain.decision_tree.paths import resolve_runtime_path


class ConditionOperations:
    run_state: RunState
    tree_key: str | None
    node_key: str | None
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
            return strict_equal(left, right)
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
            return any(strict_equal(left, item) for item in right)

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


def strict_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if type(left) in {int, float} and type(right) in {int, float}:
        return left == right
    return type(left) is type(right) and left == right

