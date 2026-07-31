import type { JsonObject, JsonValue, NodeType } from './common'

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
  inferred_follow_up_type: 'INITIAL_VISIT' | 'LIFESTYLE_FOLLOW_UP' | 'MEDICATION_FOLLOW_UP' | 'PREGNANCY_FOLLOW_UP' | null
  previous_recommended_action_types: string[]
  pregnancy_follow_up: {
    episode_id: string
    encounter_count: number
    follow_up_number: number
    phase: 'INITIAL' | 'FOLLOW_UP_1' | 'FOLLOW_UP_2' | 'FOLLOW_UP_3' | 'CONTINUING'
    minimum_follow_ups_required: number
    minimum_follow_ups_completed: boolean
    next_follow_up_number: number | null
    next_follow_up_required: boolean
    previous_visit_date: string | null
  } | null
}
