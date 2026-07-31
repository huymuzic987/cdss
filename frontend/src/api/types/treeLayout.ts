// Tree layout (mirrors src/cdss/api/schemas/tree_layout.py)

export interface TreeNodePosition {
  x: number
  y: number
}

export interface TreeEdgeLayout {
  x: number
  y: number
  bend: number
  elbowMidPoint: number
  start: { x: number; y: number }
  end: { x: number; y: number }
  start_anchor?: { x: number; y: number }
  end_anchor?: { x: number; y: number }
}
export interface TreeLayoutResponse {
  positions: Record<string, TreeNodePosition>
  arrow_kind: 'straight' | 'elbow'
  edge_layouts: Record<string, TreeEdgeLayout>
}

export interface TreeLayoutRequest {
  positions: Record<string, TreeNodePosition>
  arrow_kind: 'straight' | 'elbow'
  edge_layouts: Record<string, TreeEdgeLayout>
}
