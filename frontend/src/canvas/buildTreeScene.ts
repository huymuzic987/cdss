import { createShapeId, type Editor, type TLShapeId } from 'tldraw'
import type { TreeEdgeLayout, TreeGraphEdge, TreeGraphNode } from '../api/types'
import type { NodePosition } from '../layout/elkLayout'
import { NODE_HEIGHT, NODE_WIDTH } from '../layout/nodeDimensions'

const DEFAULT_START_ANCHOR = { x: 0.5, y: 1 }
const DEFAULT_END_ANCHOR = { x: 0.5, y: 0 }
const SAVED_ENDPOINT_TOLERANCE = 8

type Point = { x: number; y: number }

function isFinitePoint(point: Point | undefined): point is Point {
  return !!point && Number.isFinite(point.x) && Number.isFinite(point.y)
}

function isNormalizedAnchor(anchor: Point | undefined): anchor is Point {
  return (
    isFinitePoint(anchor) &&
    anchor.x >= 0 &&
    anchor.x <= 1 &&
    anchor.y >= 0 &&
    anchor.y <= 1
  )
}

function pagePoint(position: NodePosition, anchor: Point): Point {
  return {
    x: position.x + NODE_WIDTH * anchor.x,
    y: position.y + NODE_HEIGHT * anchor.y,
  }
}

function savedLayoutMatchesNodes(
  saved: TreeEdgeLayout | undefined,
  fromPosition: NodePosition,
  toPosition: NodePosition,
): saved is TreeEdgeLayout & { start_anchor: Point; end_anchor: Point } {
  if (
    !saved ||
    !Number.isFinite(saved.x) ||
    !Number.isFinite(saved.y) ||
    !isFinitePoint(saved.start) ||
    !isFinitePoint(saved.end) ||
    !isNormalizedAnchor(saved.start_anchor) ||
    !isNormalizedAnchor(saved.end_anchor)
  ) {
    return false
  }

  const savedStart = { x: saved.x + saved.start.x, y: saved.y + saved.start.y }
  const savedEnd = { x: saved.x + saved.end.x, y: saved.y + saved.end.y }
  const expectedStart = pagePoint(fromPosition, saved.start_anchor)
  const expectedEnd = pagePoint(toPosition, saved.end_anchor)

  return (
    Math.hypot(savedStart.x - expectedStart.x, savedStart.y - expectedStart.y) <= SAVED_ENDPOINT_TOLERANCE &&
    Math.hypot(savedEnd.x - expectedEnd.x, savedEnd.y - expectedEnd.y) <= SAVED_ENDPOINT_TOLERANCE
  )
}

function defaultArrowGeometry(fromPosition: NodePosition, toPosition: NodePosition) {
  const startPage = pagePoint(fromPosition, DEFAULT_START_ANCHOR)
  const endPage = pagePoint(toPosition, DEFAULT_END_ANCHOR)
  const x = Math.min(startPage.x, endPage.x)
  const y = Math.min(startPage.y, endPage.y)

  return {
    x,
    y,
    start: { x: startPage.x - x, y: startPage.y - y },
    end: { x: endPage.x - x, y: endPage.y - y },
  }
}

export function buildTreeScene(
  editor: Editor,
  nodes: TreeGraphNode[],
  edges: TreeGraphEdge[],
  positions: Map<string, NodePosition>,
  arrowKind: 'straight' | 'elbow' = 'straight',
  theme: 'dark' | 'light' = 'dark',
  edgeLayouts: Record<string, TreeEdgeLayout> = {},
): Map<string, TLShapeId> {
  const shapeIdByNodeKey = new Map<string, TLShapeId>()

  for (const node of nodes) {
    const position = positions.get(node.node_key) ?? { x: 0, y: 0 }
    const shapeId = createShapeId(node.node_key)
    shapeIdByNodeKey.set(node.node_key, shapeId)
    editor.createShape({
      id: shapeId,
      type: 'decisionNode',
      x: position.x,
      y: position.y,
      props: {
        w: NODE_WIDTH,
        h: NODE_HEIGHT,
        nodeKey: node.node_key,
        nodeType: node.node_type,
        label: node.text_en,
        theme,
      },
    })
  }

  for (const edge of edges) {
    const fromShapeId = shapeIdByNodeKey.get(edge.from_node_key)
    const toShapeId = shapeIdByNodeKey.get(edge.to_node_key)
    if (!fromShapeId || !toShapeId) continue

    const edgeKey = `${edge.from_node_key}->${edge.to_node_key}`
    const saved = edgeLayouts[edgeKey]
    const fromPosition = positions.get(edge.from_node_key) ?? { x: 0, y: 0 }
    const toPosition = positions.get(edge.to_node_key) ?? { x: 0, y: 0 }
    // Saved layouts can outlive node moves or graph changes. Keep a saved route
    // only when its page-space endpoints still meet the current node anchors;
    // otherwise reconstruct the connector from the current node positions.
    const boundSavedLayout = savedLayoutMatchesNodes(saved, fromPosition, toPosition) ? saved : undefined
    const fallbackGeometry = defaultArrowGeometry(fromPosition, toPosition)
    const arrowId = createShapeId()
    editor.createShape({
      id: arrowId,
      type: 'arrow',
      x: boundSavedLayout?.x ?? fallbackGeometry.x,
      y: boundSavedLayout?.y ?? fallbackGeometry.y,
      meta: { edgeKey },
      props: {
        kind: arrowKind === 'elbow' ? 'elbow' : 'arc',
        bend: boundSavedLayout?.bend ?? 0,
        elbowMidPoint: boundSavedLayout?.elbowMidPoint ?? 0.5,
        start: boundSavedLayout
          ? boundSavedLayout.start
          : fallbackGeometry.start,
        end: boundSavedLayout
          ? boundSavedLayout.end
          : fallbackGeometry.end,
      },
    })
    editor.createBindings([
      {
        type: 'arrow',
        fromId: arrowId,
        toId: fromShapeId,
        props: {
          terminal: 'start',
          normalizedAnchor: boundSavedLayout?.start_anchor ?? DEFAULT_START_ANCHOR,
          isExact: false,
          isPrecise: true,
          snap: 'none',
        },
      },
      {
        type: 'arrow',
        fromId: arrowId,
        toId: toShapeId,
        props: {
          terminal: 'end',
          normalizedAnchor: boundSavedLayout?.end_anchor ?? DEFAULT_END_ANCHOR,
          isExact: false,
          isPrecise: true,
          snap: 'none',
        },
      },
    ])
  }

  return shapeIdByNodeKey
}
