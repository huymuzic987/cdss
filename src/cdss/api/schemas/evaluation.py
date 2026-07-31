"""Schemas for stateless decision-tree evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cdss.domain.decision_tree import (
    ExecutedAction,
    ExecutedReference,
    JsonObject,
    RunState,
    TraversalResult,
    TraversalTraceEntry,
    TreeMetadata,
    select_output_actions,
)
from cdss.domain.follow_up import FollowUpType


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationResponse(ApiModel):
    status: Literal["success"]
    input_snapshot: JsonObject
    context: JsonObject
    actions: list[ExecutedAction]
    traversal_log: list[TraversalTraceEntry]
    references: list[ExecutedReference]
    tree_metadata: list[TreeMetadata]
    started_at: datetime
    completed_at: datetime
    inferred_follow_up_type: FollowUpType | None = None
    previous_recommended_action_types: list[str] = Field(default_factory=list)

    @classmethod
    def from_result(
        cls,
        result: TraversalResult,
        *,
        debug_output: bool = False,
        inferred_follow_up_type: FollowUpType | None = None,
        previous_recommended_action_types: list[str] | None = None,
        input_snapshot: JsonObject | None = None,
        actions: list[ExecutedAction] | None = None,
    ) -> EvaluationResponse:
        return cls(
            status=result.status,
            input_snapshot=input_snapshot or result.input_snapshot.to_dict(),
            context=result.context,
            actions=(
                actions
                if actions is not None
                else select_output_actions(result.actions, debug_output=debug_output)
            ),
            traversal_log=result.trace,
            references=result.references,
            tree_metadata=result.tree_metadata,
            started_at=result.started_at,
            completed_at=result.completed_at,
            inferred_follow_up_type=inferred_follow_up_type,
            previous_recommended_action_types=previous_recommended_action_types or [],
        )


class PartialRunStateResponse(ApiModel):
    input_snapshot: JsonObject
    context: JsonObject
    actions: list[ExecutedAction]
    traversal_log: list[TraversalTraceEntry]
    references: list[ExecutedReference]

    @classmethod
    def from_run_state(cls, run_state: RunState) -> PartialRunStateResponse:
        return cls(
            input_snapshot=run_state.input_snapshot.to_dict(),
            context=run_state.context,
            actions=run_state.actions,
            traversal_log=run_state.trace,
            references=run_state.references,
        )


class EvaluationErrorResponse(ApiModel):
    code: str
    message: str
    tree_key: str | None = None
    node_key: str | None = None
    details: JsonObject = Field(default_factory=dict)
    partial_run_state: PartialRunStateResponse | None = None
