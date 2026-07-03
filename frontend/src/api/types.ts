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
