import type { JsonObject } from './common'

export type RegimenDecisionOutcome = 'accepted' | 'rejected'
export type SelectorKind = 'group' | 'subgroup' | 'medicine'
export type DoseStrategy = 'LOW_DOSE' | 'USUAL_DOSE' | 'MAX_DOSE'
export type PlanItemType = 'NEXT_FOLLOW_UP' | 'TARGET_BP' | 'ELSE'
export type TargetMode = 'SBP_DBP' | 'MAP_REDUCTION_PERCENT'
export type DurationUnit = 'weeks' | 'months'
export type TimeframeUnit = 'days' | 'weeks' | 'months'
export type RejectionReasonCode =
  | 'DRUGS_NOT_CORRECT'
  | 'DOSE_OR_FREQUENCY_NOT_CORRECT'
  | 'SAFETY_OR_CONTRAINDICATION'
  | 'PATIENT_PREFERENCE_OR_ADHERENCE'
  | 'AVAILABILITY_OR_COST'
  | 'OTHER'

export interface RegimenComponentSelection {
  selector_kind: SelectorKind
  group_code: string
  subgroup?: string
  medicine_id?: string
  dose_strategy: DoseStrategy
}

export interface RegimenOptionInput {
  components: RegimenComponentSelection[]
}

export interface ClinicalPlanItemInput {
  type: PlanItemType
  scheduled_at?: string
  duration_value?: number
  duration_unit?: DurationUnit
  target_mode?: TargetMode
  target_sbp?: number
  target_dbp?: number
  map_reduction_percent?: number
  timeframe_value?: number
  timeframe_unit?: TimeframeUnit
  text?: string
}

export interface RegimenSnapshotInput {
  clinical_plan: ClinicalPlanItemInput[]
  regimen_options: RegimenOptionInput[]
}

export interface RegimenDecisionCreateRequest {
  outcome: RegimenDecisionOutcome
  evaluation_snapshot: JsonObject
  baseline: RegimenSnapshotInput
  final?: RegimenSnapshotInput
  rejection_reasons: RejectionReasonCode[]
  other_rejection_reason?: string
}

export interface RegimenDecisionResponse {
  id: string
  outcome: RegimenDecisionOutcome
  patient_fhir_id: string
  encounter_fhir_id: string | null
  created_at: string
}

export interface CatalogMedicine {
  drug_id: string
  name: string
  group_code: string
  subgroup: string | null
  route: string | null
  dose_low: string | null
  dose_usual: string | null
  dose_max: string | null
  available: boolean
  snomed_code: string | null
}

export interface CatalogSubgroup {
  name: string
  medicines: CatalogMedicine[]
}

export interface CatalogGroup {
  code: string
  label_en: string
  label_vi: string
  subgroups: CatalogSubgroup[]
}

export interface MedicineCatalogResponse {
  groups: CatalogGroup[]
}
