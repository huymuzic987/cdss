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
    risk_factor_distribution: list[Count]


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
    sbp_severity_distribution: list[Count]
    mean_sbp: float | None
    median_sbp: float | None


class CdssUsageResponse(ApiModel):
    facility_capability_distribution: list[Count]
    hypertension_class_distribution: list[Count]
    risk_level_distribution: list[Count]
    recommended_action_frequency: list[Count]
    drug_class_distribution: list[Count]


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
    adherent_visit_count: int
    non_adherent_visit_count: int


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


class DashboardSummaryResponse(ApiModel):
    """Everything the dashboard page needs in one response, built from a
    single patient load instead of the 7 separate round trips the old
    per-metric endpoints each required."""

    overview: OverviewResponse
    visits: VisitsResponse
    outcomes: OutcomesResponse
    cdss_usage: CdssUsageResponse
    efficacy: EfficacyResponse
    fhir_import_status: FhirImportStatusResponse
    needs_attention: NeedsAttentionResponse


class VisitMedicationSummary(ApiModel):
    drug_id: str | None
    drug_name: str
    drug_class_note: str | None
    dose_value: float | None
    dose_unit: str | None


class VisitObservationSummary(ApiModel):
    loinc_code: str
    display_name: str | None
    value: float
    unit: str | None


class PatientVisitDetail(ApiModel):
    visit_number: int
    visit_date: date
    facility_capability: str | None
    is_early_revisit: bool
    early_revisit_reason: str | None
    scheduled_next_visit_date: date | None
    clinic_sbp: int | None
    clinic_dbp: int | None
    bp_target_sbp: int | None
    bp_target_dbp: int | None
    bp_controlled: bool | None
    hypertension_class: str | None
    risk_level: str | None
    cdss_recommended_action: str | None
    adherent_to_cdss: bool | None
    medications: list[VisitMedicationSummary]
    observations: list[VisitObservationSummary]


class PatientConditionSummary(ApiModel):
    icd10_code: str | None
    snomed_code: str | None
    condition_text: str | None


class PatientDetailResponse(ApiModel):
    fhir_id: str
    gender: str | None
    birth_date: date | None
    department: str | None
    risk_factor_count: int
    conditions: list[PatientConditionSummary]
    visits: list[PatientVisitDetail]


class PatientListItem(ApiModel):
    fhir_id: str
    gender: str | None
    birth_date: date | None
    department: str | None
    last_visit_date: date | None
    visit_count: int
    last_bp_controlled: bool | None
    last_risk_level: str | None
    is_overdue: bool


class PatientListResponse(ApiModel):
    items: list[PatientListItem]
    total: int


class ContributorMetricResponse(ApiModel):
    member_key: str
    display_name: str
    canonical_email: str
    github_username: str | None
    commits: int
    commits_percentage: float
    lines_added: int
    lines_added_percentage: float
    lines_deleted: int
    total_loc_changes: int
    total_loc_percentage: float
    primary_role: str
    deliverables: list[str]


class ContributionSummaryResponse(ApiModel):
    total_commits: int
    total_lines_added: int
    total_lines_deleted: int
    total_loc_changes: int
    active_contributors: int


class OverlappingTaskResponse(ApiModel):
    feature_area: str
    collaborators: list[str]
    shared_deliverables: str


class RecentCommitItem(ApiModel):
    hash: str
    author: str
    message: str
    timestamp: int


class ContributionsResponse(ApiModel):
    summary: ContributionSummaryResponse
    contributors: list[ContributorMetricResponse]
    overlapping_matrix: list[OverlappingTaskResponse]
    recent_commits: list[RecentCommitItem]
    scope: str
    updated_at: datetime
