"""Serializable contracts for medication regimen construction."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from cdss.domain.decision_tree.contracts import RuntimeModel

DEFAULT_REGIMEN_DOSE_STRATEGY = "LOW_DOSE"


class RegimenKeyword(StrEnum):
    DETERMINE = "DETERMINE"
    CLASSIFY = "CLASSIFY"
    SET = "SET"
    RESTORE = "RESTORE"
    EVALUATE = "EVALUATE"
    COMPARE = "COMPARE"
    TEST = "TEST"
    START = "START"
    ADD = "ADD"
    COMBINE = "COMBINE"
    SELECT = "SELECT"
    ADJUST = "ADJUST"
    CHANGE = "CHANGE"
    ESCALATE = "ESCALATE"
    REDUCE = "REDUCE"
    STOP = "STOP"
    KEEP = "KEEP"
    MAINTAIN = "MAINTAIN"
    MONITOR = "MONITOR"
    AVOID = "AVOID"


class RegimenComponent(RuntimeModel):
    selector_kind: Literal["class", "medicine"]
    code: str | None = None
    medicine_id: str | None = None
    name: str | None = None
    dose_strategy: str = DEFAULT_REGIMEN_DOSE_STRATEGY
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None


class RegimenAlternative(RuntimeModel):
    components: list[RegimenComponent] = Field(default_factory=list)


class RegimenUpdateStep(RuntimeModel):
    id: str
    trace_step: int
    tree_key: str
    node_key: str
    keyword: RegimenKeyword
    text_en: str
    text_vi: str
    source: Literal["structured", "context", "legacy"]
    components: list[RegimenComponent] = Field(default_factory=list)
    alternatives: list[RegimenAlternative] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EffectiveMedicationRegimen(RuntimeModel):
    base_options: list[RegimenAlternative] = Field(default_factory=list)
    additions: list[RegimenComponent] = Field(default_factory=list)
    adjustments: list[RegimenUpdateStep] = Field(default_factory=list)
    stopped_components: list[RegimenComponent] = Field(default_factory=list)
    constraints: list[RegimenComponent] = Field(default_factory=list)
    status: Literal["complete", "partial", "choice_required", "conflict"] = "complete"


class MedicationRegimenPlan(RuntimeModel):
    schema_version: Literal["1.0"] = "1.0"
    steps: list[RegimenUpdateStep] = Field(default_factory=list)
    effective_regimen: EffectiveMedicationRegimen = Field(
        default_factory=EffectiveMedicationRegimen
    )
    catalog_by_class: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    catalog: list[dict[str, Any]] = Field(default_factory=list)
