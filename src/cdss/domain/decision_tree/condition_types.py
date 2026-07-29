"""Shared condition evaluation types and dialect constants."""

from pydantic import Field

from cdss.domain.decision_tree.contracts import JsonObject, RuntimeModel

LOGICAL_FORMS = frozenset({"all", "any", "not"})
SUPPORTED_OPERATORS = frozenset({"eq", "exists", "in", "lt", "lte", "gt", "gte"})


class ConditionEvaluation(RuntimeModel):
    result: bool
    details: JsonObject = Field(default_factory=dict)
