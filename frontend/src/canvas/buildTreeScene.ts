import { createShapeId, type Editor, type TLShapeId } from 'tldraw'
import type { TreeEdgeLayout, TreeGraphEdge, TreeGraphNode } from '../api/types'
import type { NodePosition } from '../layout/elkLayout'
import { NODE_HEIGHT, NODE_WIDTH } from '../layout/nodeDimensions'

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
    // Older saved layouts did not persist binding anchors. Their absolute
    // arrow coordinates can become detached after a node or edge is added,
    // so use a fresh node-to-node geometry until a fully bound layout exists.
    const boundSavedLayout = saved?.start_anchor && saved?.end_anchor ? saved : undefined
    const arrowId = createShapeId()
    editor.createShape({
      id: arrowId,
      type: 'arrow',
      x: boundSavedLayout?.x ?? 0,
      y: boundSavedLayout?.y ?? 0,
      meta: { edgeKey },
      props: {
        kind: arrowKind === 'elbow' ? 'elbow' : 'arc',
        bend: boundSavedLayout?.bend ?? 0,
        elbowMidPoint: boundSavedLayout?.elbowMidPoint ?? 0.5,
        start: boundSavedLayout
          ? boundSavedLayout.start
          : { x: fromPosition.x + NODE_WIDTH / 2, y: fromPosition.y + NODE_HEIGHT },
        end: boundSavedLayout
          ? boundSavedLayout.end
          : { x: toPosition.x + NODE_WIDTH / 2, y: toPosition.y },
      },
    })
    editor.createBindings([
      {
        type: 'arrow',
        fromId: arrowId,
        toId: fromShapeId,
        props: {
          terminal: 'start',
          normalizedAnchor: saved?.start_anchor ?? { x: 0.5, y: 1 },
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
          normalizedAnchor: saved?.end_anchor ?? { x: 0.5, y: 0 },
          isExact: false,
          isPrecise: true,
          snap: 'none',
        },
      },
    ])
  }

  return shapeIdByNodeKey
}
