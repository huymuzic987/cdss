// Mirrors src/cdss/api/schemas/tree_graph.py

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }

export type JsonObject = { [key: string]: JsonValue }

export type NodeType =
  | 'START'
  | 'CONDITION'
  | 'INFERENCE'
  | 'ACTION'
  | 'END'
  | 'LINK'
  | 'GLOBAL'

export interface TreeSummary {
  tree_key: string
  name_en: string
  name_vi: string
}

export interface TreeGraphNode {
  node_key: string
  node_type: NodeType
  text_en: string
  text_vi: string
  condition_definition: JsonObject | null
  context_patch: JsonObject | null
  action_payload: JsonObject | null
  link_target_tree_key: string | null
  link_target_node_key: string | null
  display_order: number
}

export interface TreeGraphEdge {
  from_node_key: string
  to_node_key: string
  traversal_order: number
}

export interface TreeGraphSourceReference {
  node_key: string
  source_title: string
  section_path: JsonValue
  reference_order: number
  locator: string | null
  locator_detail: string | null
  reference_note: string | null
}

export interface TreeGraphGlobalNode {
  node_key: string
  text_en: string
  text_vi: string
  global_config: JsonObject | null
  display_order: number
}

export interface TreeGraphResponse {
  tree: TreeSummary
  start_node_key: string
  nodes: TreeGraphNode[]
  edges: TreeGraphEdge[]
  global_nodes: TreeGraphGlobalNode[]
  references: TreeGraphSourceReference[]
}

// ---- Tree layout (mirrors src/cdss/api/schemas/tree_layout.py) ----

export interface TreeNodePosition {
  x: number
  y: number
}

export interface TreeLayoutResponse {
  positions: Record<string, TreeNodePosition>
  arrow_kind: 'straight' | 'elbow'
}

export interface TreeLayoutRequest {
  positions: Record<string, TreeNodePosition>
  arrow_kind: 'straight' | 'elbow'
}

export interface ApiErrorResponse {
  code: string
  message: string
  tree_key?: string | null
  node_key?: string | null
  details?: { [key: string]: JsonValue }
  partial_run_state?: PartialRunState | null
}

export type TraceEvent = 'node_entered' | 'candidate_evaluated'

export interface TraversalTraceEntry {
  step: number
  event: TraceEvent
  tree_key: string
  node_key: string
  node_type: NodeType
  candidate_node_key: string | null
  condition_definition: JsonObject | null
  condition_result: boolean | null
  evaluation_details: JsonObject | null
  changed_context_paths: string[]
}

export interface ExecutedAction {
  tree_key: string
  node_key: string
  node_type: NodeType
  text_en: string
  text_vi: string
  payload: JsonObject
}

export interface ExecutedReference {
  tree_key: string
  node_key: string
  reference_order: number
  source_title: string
  section_path: JsonValue
  locator: string | null
  locator_detail: string | null
  reference_note: string | null
}

export interface PartialRunState {
  input_snapshot: JsonObject
  context: JsonObject
  actions: ExecutedAction[]
  traversal_log: TraversalTraceEntry[]
  references: ExecutedReference[]
}

export interface EvaluationResponse {
  status: 'success'
  input_snapshot: JsonObject
  context: JsonObject
  actions: ExecutedAction[]
  traversal_log: TraversalTraceEntry[]
  references: ExecutedReference[]
  tree_metadata: { tree_key: string; name_en: string; name_vi: string }[]
  started_at: string
  completed_at: string
}

export interface EvaluationRequest {
  start_tree_key: string
  input: JsonObject
}

// ---- Dashboard (mirrors src/cdss/api/schemas/dashboard.py) ----

export interface Count {
  label: string
  count: number
}

export interface RatePoint {
  label: string
  count: number
  rate: number
}

export interface OverviewResponse {
  total_patients: number
  total_visits: number
  new_patients_last_30_days: number
  age_distribution: Count[]
  gender_distribution: Count[]
  comorbidity_prevalence: RatePoint[]
}

export interface OverdueVisit {
  patient_fhir_id: string
  last_visit_date: string
  scheduled_next_visit_date: string
  days_overdue: number
}

export interface VisitsResponse {
  total_visits: number
  follow_up_visit_count: number
  on_schedule_rate: number
  early_revisit_rate: number
  early_revisit_reason_breakdown: Count[]
  avg_days_between_visits: number | null
  visits_by_visit_number: Count[]
  overdue_patients: OverdueVisit[]
}

export interface VisitNumberOutcome {
  visit_number: number
  count: number
  bp_controlled_rate: number
  avg_sbp: number | null
  avg_dbp: number | null
}

export interface OutcomesResponse {
  bp_target_distribution: Count[]
  outcomes_by_visit_number: VisitNumberOutcome[]
}

export interface CdssUsageResponse {
  facility_capability_distribution: Count[]
  hypertension_class_distribution: Count[]
  risk_level_distribution: Count[]
  recommended_action_frequency: Count[]
}

export interface AdherenceByVisitNumber {
  visit_number: number
  adherence_rate: number
  count: number
}

export interface EfficacyResponse {
  overall_adherence_rate: number
  bp_control_rate_when_adherent: number
  bp_control_rate_when_not_adherent: number
  effectiveness_delta: number
  medication_change_count: number
  medication_change_rate: number
  adherence_rate_by_visit_number: AdherenceByVisitNumber[]
}

export interface ImportBatchSummary {
  source_label: string
  imported_at: string
  patient_count: number
  visit_count: number
  error_count: number
}

export interface FhirImportStatusResponse {
  batches: ImportBatchSummary[]
  total_patients: number
  total_encounters: number
  total_observations: number
  total_medication_requests: number
}

export interface NeedsAttentionPatient {
  patient_fhir_id: string
  reasons: string[]
  last_visit_date: string
  clinic_sbp: number | null
  clinic_dbp: number | null
  bp_target_sbp: number | null
  bp_target_dbp: number | null
}

export interface NeedsAttentionResponse {
  patients: NeedsAttentionPatient[]
}

export interface ImportResult {
  source_label: string
  patients_imported: number
  visits_imported: number
  error_count: number
  errors: { resource: string; message: string }[]
}

export interface DashboardFilters {
  facility_capability?: string
  comorbidity_icd10?: string
}
