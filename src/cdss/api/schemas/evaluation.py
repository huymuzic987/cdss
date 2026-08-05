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
from cdss.domain.decision_tree.contracts import copy_json_value
from cdss.domain.follow_up import FollowUpType
from cdss.domain.pregnancy_follow_up import (
    PregnancyFollowUpPhase,
    PregnancyFollowUpSummary,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PregnancyFollowUpResponse(ApiModel):
    episode_id: str
    encounter_count: int
    follow_up_number: int
    phase: PregnancyFollowUpPhase
    minimum_follow_ups_required: int
    minimum_follow_ups_completed: bool
    next_follow_up_number: int | None
    next_follow_up_required: bool
    previous_visit_date: str | None

    @classmethod
    def from_summary(cls, summary: PregnancyFollowUpSummary) -> PregnancyFollowUpResponse:
        return cls(**summary.__dict__)


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
    pregnancy_follow_up: PregnancyFollowUpResponse | None = None

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
        pregnancy_follow_up: PregnancyFollowUpSummary | None = None,
    ) -> EvaluationResponse:
        return cls(
            status=result.status,
            input_snapshot=input_snapshot or result.input_snapshot.to_dict(),
            context=_json_object(result.context),
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
            pregnancy_follow_up=(
                PregnancyFollowUpResponse.from_summary(pregnancy_follow_up)
                if pregnancy_follow_up
                else None
            ),
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
            context=_json_object(run_state.context),
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


def _json_object(value: JsonObject) -> JsonObject:
    copied = copy_json_value(value)
    if not isinstance(copied, dict):
        raise TypeError("response value must be a JSON object")
    return copied
