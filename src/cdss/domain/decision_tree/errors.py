"""Typed, serializable domain errors for decision-tree execution."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, ClassVar

from cdss.domain.decision_tree.contracts import JsonObject, RunState


class DecisionTreeError(Exception):
    code: ClassVar[str] = "decision_tree_error"
    default_message: ClassVar[str] = "Decision-tree execution failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        tree_key: str | None = None,
        node_key: str | None = None,
        details: JsonObject | None = None,
        partial_run_state: RunState | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.tree_key = tree_key
        self.node_key = node_key
        self.details = deepcopy(details) if details is not None else {}
        self.partial_run_state = (
            partial_run_state.snapshot() if partial_run_state is not None else None
        )
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON-compatible error representation."""

        return {
            "code": self.code,
            "message": self.message,
            "tree_key": self.tree_key,
            "node_key": self.node_key,
            "details": deepcopy(self.details),
            "partial_run_state": (
                self.partial_run_state.model_dump(mode="json")
                if self.partial_run_state is not None
                else None
            ),
        }


class TreeNotFound(DecisionTreeError):
    code = "tree_not_found"
    default_message = "Decision tree was not found."


class InvalidTreeStructure(DecisionTreeError):
    code = "invalid_tree_structure"
    default_message = "Decision tree structure is invalid."


class InvalidStartNode(DecisionTreeError):
    code = "invalid_start_node"
    default_message = "Decision tree must have exactly one valid START node."


class InvalidConditionDefinition(DecisionTreeError):
    code = "invalid_condition_definition"
    default_message = "Condition definition is invalid."


class UnsupportedOperator(DecisionTreeError):
    code = "unsupported_operator"
    default_message = "Condition operator is not supported."


class MissingRuntimePath(DecisionTreeError):
    code = "missing_runtime_path"
    default_message = "A required runtime path is missing."


class InvalidRuntimeValueType(DecisionTreeError):
    code = "invalid_runtime_value_type"
    default_message = "A runtime value has an invalid type."


class ContextPatchError(DecisionTreeError):
    code = "context_patch_error"
    default_message = "Context patch could not be applied."


class NoMatchingTransition(DecisionTreeError):
    code = "no_matching_transition"
    default_message = "No outgoing transition matched."


class LinkTargetNotFound(DecisionTreeError):
    code = "link_target_not_found"
    default_message = "Linked decision tree was not found."


class LinkTargetNodeNotFound(DecisionTreeError):
    code = "link_target_node_not_found"
    default_message = "Linked target node was not found."


class TraversalCycleDetected(DecisionTreeError):
    code = "traversal_cycle_detected"
    default_message = "Decision-tree traversal encountered a cycle."


class TraversalLimitExceeded(DecisionTreeError):
    code = "traversal_limit_exceeded"
    default_message = "Decision-tree traversal exceeded its step limit."


class LinkNotEnabled(DecisionTreeError):
    code = "link_not_enabled"
    default_message = "Cross-tree link execution is not enabled."
