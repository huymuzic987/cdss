"""Schemas for stateless decision-tree evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationRequest(ApiModel):
    start_tree_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    input: Annotated[
        JsonObject,
        Field(
            description=(
                "An HL7 FHIR R4 Bundle (resourceType == 'Bundle'); see "
                "cdss.api.schemas.fhir_input for the resource-mapping contract."
            )
        ),
    ]


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

    @classmethod
    def from_result(
        cls, result: TraversalResult, *, debug_output: bool = False
    ) -> EvaluationResponse:
        return cls(
            status=result.status,
            input_snapshot=result.input_snapshot.to_dict(),
            context=result.context,
            actions=select_output_actions(result.actions, debug_output=debug_output),
            traversal_log=result.trace,
            references=result.references,
            tree_metadata=result.tree_metadata,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )


class FollowUpEvaluationRequest(ApiModel):
    input: Annotated[
        JsonObject,
        Field(
            description=(
                "An HL7 FHIR R4 Bundle (resourceType == 'Bundle') carrying "
                "facility_capability, medication_follow_up_stage, "
                "active_bp_target, current_clinic_sbp, and current_clinic_dbp; "
                "see cdss.api.schemas.fhir_input for the resource-mapping contract."
            )
        ),
    ]


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
