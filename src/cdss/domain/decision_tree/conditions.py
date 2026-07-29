"""Public API for decision-tree condition evaluation and validation."""

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.condition_evaluator import ConditionEvaluator
from cdss.domain.decision_tree.condition_types import ConditionEvaluation
from cdss.domain.decision_tree.condition_validation import ConditionDefinitionValidator
from cdss.domain.decision_tree.contracts import NodeType, RunState
from cdss.domain.decision_tree.errors import InvalidConditionDefinition


def evaluate_condition(
    condition_definition: Mapping[str, Any] | None,
    run_state: RunState,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
) -> ConditionEvaluation:
    validate_condition_definition(
        condition_definition,
        tree_key=tree_key,
        node_key=node_key,
        partial_run_state=run_state,
    )
    return ConditionEvaluator(run_state, tree_key=tree_key, node_key=node_key).evaluate(
        condition_definition
    )


def validate_condition_definition(
    condition_definition: Mapping[str, Any] | None,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
    partial_run_state: RunState | None = None,
) -> None:
    ConditionDefinitionValidator(
        tree_key=tree_key,
        node_key=node_key,
        partial_run_state=partial_run_state,
    ).validate(condition_definition)


def evaluate_candidate_condition(
    node_type: NodeType,
    condition_definition: Mapping[str, Any] | None,
    run_state: RunState,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
) -> ConditionEvaluation:
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
