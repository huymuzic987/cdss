"""Result types returned by tree validation."""

from pydantic import Field

from cdss.domain.decision_tree.contracts import JsonObject, RuntimeModel


class TreeValidationWarning(RuntimeModel):
    code: str
    message: str
    tree_key: str
    node_key: str | None = None
    details: JsonObject = Field(default_factory=dict)


class TreeValidationResult(RuntimeModel):
    tree_key: str
    warnings: list[TreeValidationWarning] = Field(default_factory=list)
