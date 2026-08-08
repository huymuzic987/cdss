"""Contracts for clinician-authored regimen decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from cdss.api.schemas.evaluation import ApiModel
from cdss.domain.decision_tree.contracts import JsonObject

Outcome = Literal["accepted", "rejected"]
SelectorKind = Literal["group", "subgroup", "medicine"]
DoseStrategy = Literal["LOW_DOSE", "USUAL_DOSE", "MAX_DOSE"]
PlanItemType = Literal["NEXT_FOLLOW_UP", "TARGET_BP", "ELSE"]
TargetMode = Literal["SBP_DBP", "MAP_REDUCTION_PERCENT"]
DurationUnit = Literal["weeks", "months"]
TimeframeUnit = Literal["days", "weeks", "months"]
ReasonCode = Literal[
    "DRUGS_NOT_CORRECT",
    "DOSE_OR_FREQUENCY_NOT_CORRECT",
    "SAFETY_OR_CONTRAINDICATION",
    "PATIENT_PREFERENCE_OR_ADHERENCE",
    "AVAILABILITY_OR_COST",
    "OTHER",
]


class RegimenComponentSelection(ApiModel):
    selector_kind: SelectorKind
    group_code: str
    subgroup: str | None = None
    medicine_id: str | None = None
    dose_strategy: DoseStrategy = "LOW_DOSE"


class RegimenOptionInput(ApiModel):
    components: list[RegimenComponentSelection] = Field(default_factory=list)


class ClinicalPlanItemInput(ApiModel):
    type: PlanItemType
    scheduled_at: datetime | None = None
    duration_value: float | None = Field(default=None, gt=0)
    duration_unit: DurationUnit | None = None
    target_mode: TargetMode | None = None
    target_sbp: int | None = Field(default=None, ge=1, le=400)
    target_dbp: int | None = Field(default=None, ge=1, le=300)
    map_reduction_percent: float | None = Field(default=None, gt=0, le=100)
    timeframe_value: float | None = Field(default=None, gt=0)
    timeframe_unit: TimeframeUnit | None = None
    text: str | None = None


class RegimenSnapshotInput(ApiModel):
    clinical_plan: list[ClinicalPlanItemInput] = Field(default_factory=list)
    regimen_options: list[RegimenOptionInput] = Field(default_factory=list)


class RegimenDecisionCreateRequest(ApiModel):
    outcome: Outcome
    evaluation_snapshot: JsonObject
    baseline: RegimenSnapshotInput
    final: RegimenSnapshotInput | None = None
    rejection_reasons: list[ReasonCode] = Field(default_factory=list)
    other_rejection_reason: str | None = None


class RegimenDecisionResponse(ApiModel):
    id: UUID
    outcome: Outcome
    patient_fhir_id: str
    encounter_fhir_id: str | None
    created_at: datetime


class CatalogMedicine(ApiModel):
    drug_id: str
    name: str
    group_code: str
    subgroup: str | None
    route: str | None
    dose_low: str | None
    dose_usual: str | None
    dose_max: str | None
    available: bool
    snomed_code: str | None


class CatalogSubgroup(ApiModel):
    name: str
    medicines: list[CatalogMedicine]


class CatalogGroup(ApiModel):
    code: str
    label_en: str
    label_vi: str
    subgroups: list[CatalogSubgroup]


class MedicineCatalogResponse(ApiModel):
    groups: list[CatalogGroup]
