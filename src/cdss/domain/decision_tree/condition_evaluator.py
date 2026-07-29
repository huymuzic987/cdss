"""Recursive evaluation of validated condition expressions."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cdss.domain.decision_tree.condition_operations import ConditionOperations
from cdss.domain.decision_tree.condition_types import (
    LOGICAL_FORMS,
    SUPPORTED_OPERATORS,
    ConditionEvaluation,
)
from cdss.domain.decision_tree.contracts import RunState, copy_json_value
from cdss.domain.decision_tree.errors import MissingRuntimePath, UnsupportedOperator
from cdss.domain.decision_tree.paths import resolve_runtime_path


@dataclass(frozen=True, slots=True)
class ConditionEvaluator(ConditionOperations):
    run_state: RunState
    tree_key: str | None
    node_key: str | None

    def evaluate(self, expression: Mapping[str, Any] | None) -> ConditionEvaluation:
        if expression is None:
            raise self._invalid("null_condition_definition")
        if not isinstance(expression, Mapping):
            raise self._invalid("condition_must_be_object")

        logical_forms = LOGICAL_FORMS.intersection(expression)
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
        if operator not in SUPPORTED_OPERATORS:
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





