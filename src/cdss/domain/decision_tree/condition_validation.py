"""Static validation for the decision-tree condition dialect."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cdss.domain.decision_tree.condition_types import LOGICAL_FORMS, SUPPORTED_OPERATORS
from cdss.domain.decision_tree.contracts import RunState, copy_json_value
from cdss.domain.decision_tree.errors import InvalidConditionDefinition, UnsupportedOperator


@dataclass(frozen=True, slots=True)
class ConditionDefinitionValidator:
    tree_key: str | None
    node_key: str | None
    partial_run_state: RunState | None

    def validate(self, expression: Mapping[str, Any] | None) -> None:
        if expression is None:
            raise self._invalid("null_condition_definition")
        if not isinstance(expression, Mapping):
            raise self._invalid("condition_must_be_object")

        logical_forms = LOGICAL_FORMS.intersection(expression)
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
        if operator not in SUPPORTED_OPERATORS:
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



