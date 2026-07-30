// Mirrors src/cdss/api/schemas/tree_graph.py

import type { JsonObject, JsonValue, NodeType } from './common'

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
