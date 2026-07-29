"""Serializable runtime contracts for decision-tree execution."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from copy import deepcopy
from datetime import datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class FrozenJsonObject(Mapping[str, Any]):
    """Recursively immutable JSON object with an explicit mutable export."""

    __slots__ = ("__data",)

    def __init__(self, value: Mapping[str, Any]) -> None:
        frozen = {key: _freeze_json(item) for key, item in value.items()}
        if any(not isinstance(key, str) for key in frozen):
            raise TypeError("JSON object keys must be strings")
        self.__data = MappingProxyType(frozen)

    def __getitem__(self, key: str) -> Any:
        return self.__data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.__data)

    def __len__(self) -> int:
        return len(self.__data)

    def __deepcopy__(self, memo: dict[int, Any]) -> FrozenJsonObject:
        return self

    def to_dict(self) -> JsonObject:
        """Return a detached, mutable JSON representation."""

        return {key: _thaw_json(value) for key, value in self.__data.items()}


def _freeze_json(value: Any) -> Any:
    if isinstance(value, FrozenJsonObject):
        return value
    if isinstance(value, Mapping):
        return FrozenJsonObject(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is float and isfinite(value):
        return value
    raise TypeError(f"value of type {type(value).__name__} is not valid JSON")


def _thaw_json(value: Any) -> JsonValue:
    if isinstance(value, FrozenJsonObject):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def copy_json_value(value: Any) -> JsonValue:
    """Return a detached mutable copy of a JSON value."""

    if isinstance(value, FrozenJsonObject):
        return value.to_dict()
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return {key: copy_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [copy_json_value(item) for item in value]
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is float and isfinite(value):
        return value
    raise TypeError(f"value of type {type(value).__name__} is not valid JSON")


class RuntimeModel(BaseModel):
    """Shared validation and serialization behavior for runtime contracts."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        validate_assignment=True,
    )


class NodeType(StrEnum):
    START = "START"
    CONDITION = "CONDITION"
    INFERENCE = "INFERENCE"
    ACTION = "ACTION"
    END = "END"
    LINK = "LINK"
    GLOBAL = "GLOBAL"


class TraceEvent(StrEnum):
    NODE_ENTERED = "node_entered"
    CANDIDATE_EVALUATED = "candidate_evaluated"


class ExecutedAction(RuntimeModel):
    tree_key: str
    node_key: str
    node_type: NodeType
    text_en: str
    text_vi: str
    payload: JsonObject


class TraversalTraceEntry(RuntimeModel):
    step: int = Field(ge=1)
    event: TraceEvent
    tree_key: str
    node_key: str
    node_type: NodeType
    candidate_node_key: str | None = None
    condition_definition: JsonObject | None = None
    condition_result: bool | None = None
    evaluation_details: JsonObject | None = None
    changed_context_paths: list[str] = Field(default_factory=list)


class ExecutedReference(RuntimeModel):
    tree_key: str
    node_key: str
    reference_order: int
    source_title: str
    section_path: JsonValue
    locator: str | None = None
    locator_detail: str | None = None
    printed_page_numbers: list[int] | None = None
    pdf_page_numbers: list[int] | None = None
    reference_note: str | None = None


class TreeMetadata(RuntimeModel):
    tree_key: str
    name_en: str
    name_vi: str
    tree_id: UUID | None = None
    global_config: list[JsonObject] = Field(default_factory=list)


class RunState(RuntimeModel):
    input_snapshot: FrozenJsonObject = Field(frozen=True)
    context: JsonObject = Field(default_factory=dict)
    actions: list[ExecutedAction] = Field(default_factory=list)
    trace: list[TraversalTraceEntry] = Field(default_factory=list)
    references: list[ExecutedReference] = Field(default_factory=list)

    @field_validator("input_snapshot", mode="before")
    @classmethod
    def _freeze_input_snapshot(cls, value: Any) -> FrozenJsonObject:
        if isinstance(value, FrozenJsonObject):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("input_snapshot must be a JSON object")
        return FrozenJsonObject(value)

    @field_serializer("input_snapshot")
    def _serialize_input_snapshot(self, value: FrozenJsonObject) -> JsonObject:
        return value.to_dict()

    @classmethod
    def initialize(cls, runtime_input: Mapping[str, Any]) -> RunState:
        """Start a run with an immutable snapshot and empty execution state."""
        instance = cls(input_snapshot=FrozenJsonObject(runtime_input))

        # Derive current clinic BP and save in context.diagnosis
        sbp = runtime_input.get("current_clinic_sbp")
        dbp = runtime_input.get("current_clinic_dbp")

        if sbp is not None and dbp is not None:
            diagnosis = instance.context.setdefault("diagnosis", {})
            if isinstance(diagnosis, dict):
                diagnosis["current_clinic_sbp"] = sbp
                diagnosis["current_clinic_dbp"] = dbp

        return instance

    def next_trace_step(self) -> int:
        """Return the next monotonically increasing trace step."""

        return self.trace[-1].step + 1 if self.trace else 1

    def snapshot(self) -> RunState:
        """Create a detached state snapshot for results and failures."""

        return self.model_copy(deep=True)


class TraversalResult(RuntimeModel):
    status: Literal["success"] = "success"
    input_snapshot: FrozenJsonObject = Field(frozen=True)
    context: JsonObject = Field(default_factory=dict)
    actions: list[ExecutedAction] = Field(default_factory=list)
    trace: list[TraversalTraceEntry] = Field(default_factory=list)
    references: list[ExecutedReference] = Field(default_factory=list)
    tree_metadata: list[TreeMetadata] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime

    @field_validator("input_snapshot", mode="before")
    @classmethod
    def _freeze_input_snapshot(cls, value: Any) -> FrozenJsonObject:
        if isinstance(value, FrozenJsonObject):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("input_snapshot must be a JSON object")
        return FrozenJsonObject(value)

    @field_serializer("input_snapshot")
    def _serialize_input_snapshot(self, value: FrozenJsonObject) -> JsonObject:
        return value.to_dict()

    @classmethod
    def from_run_state(
        cls,
        run_state: RunState,
        *,
        tree_metadata: list[TreeMetadata],
        started_at: datetime,
        completed_at: datetime,
    ) -> TraversalResult:
        """Freeze a successful run into a result detached from later mutations."""

        state = run_state.snapshot()
        return cls(
            input_snapshot=state.input_snapshot,
            context=deepcopy(state.context),
            actions=deepcopy(state.actions),
            trace=deepcopy(state.trace),
            references=deepcopy(state.references),
            tree_metadata=deepcopy(tree_metadata),
            started_at=started_at,
            completed_at=completed_at,
        )
