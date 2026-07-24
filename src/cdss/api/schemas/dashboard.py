"""Response schemas for the statistics dashboard endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Count(ApiModel):
    label: str
    count: int


class RatePoint(ApiModel):
    label: str
    count: int
    rate: float


class OverviewResponse(ApiModel):
    total_patients: int
    total_visits: int
    new_patients_last_30_days: int
    age_distribution: list[Count]
    gender_distribution: list[Count]
    comorbidity_prevalence: list[RatePoint]


class OverdueVisit(ApiModel):
    patient_fhir_id: str
    last_visit_date: date
    scheduled_next_visit_date: date
    days_overdue: int


class VisitsResponse(ApiModel):
    total_visits: int
    follow_up_visit_count: int
    on_schedule_rate: float
    early_revisit_rate: float
    early_revisit_reason_breakdown: list[Count]
    avg_days_between_visits: float | None
    visits_by_visit_number: list[Count]
    overdue_patients: list[OverdueVisit]


class VisitNumberOutcome(ApiModel):
    visit_number: int
    count: int
    bp_controlled_rate: float
    avg_sbp: float | None
    avg_dbp: float | None


class OutcomesResponse(ApiModel):
    bp_target_distribution: list[Count]
    outcomes_by_visit_number: list[VisitNumberOutcome]


class CdssUsageResponse(ApiModel):
    facility_capability_distribution: list[Count]
    hypertension_class_distribution: list[Count]
    risk_level_distribution: list[Count]
    recommended_action_frequency: list[Count]


class AdherenceByVisitNumber(ApiModel):
    visit_number: int
    adherence_rate: float
    count: int


class EfficacyResponse(ApiModel):
    overall_adherence_rate: float
    # Rate at which the *following* visit reaches BP control, conditioned on
    # whether the clinician followed the CDSS recommendation at the prior
    # (uncontrolled) visit -- not same-visit correlation, which is circular.
    bp_control_rate_when_adherent: float
    bp_control_rate_when_not_adherent: float
    effectiveness_delta: float
    medication_change_count: int
    medication_change_rate: float
    adherence_rate_by_visit_number: list[AdherenceByVisitNumber]


class ImportBatchSummary(ApiModel):
    source_label: str
    imported_at: datetime
    patient_count: int
    visit_count: int
    error_count: int


class FhirImportStatusResponse(ApiModel):
    batches: list[ImportBatchSummary]
    total_patients: int
    total_encounters: int
    total_observations: int
    total_medication_requests: int


class NeedsAttentionPatient(ApiModel):
    patient_fhir_id: str
    reasons: list[str]
    last_visit_date: date
    clinic_sbp: int | None
    clinic_dbp: int | None
    bp_target_sbp: int | None
    bp_target_dbp: int | None


class NeedsAttentionResponse(ApiModel):
    patients: list[NeedsAttentionPatient]
