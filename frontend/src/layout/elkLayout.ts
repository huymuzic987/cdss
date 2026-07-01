import ELK from 'elkjs/lib/elk.bundled.js'
import type { TreeGraphEdge, TreeGraphNode } from '../api/types'

export const NODE_WIDTH = 220
export const NODE_HEIGHT = 72

export interface NodePosition {
  x: number
  y: number
}

const elk = new ELK()

export async function layoutTree(
  nodes: TreeGraphNode[],
  edges: TreeGraphEdge[],
): Promise<Map<string, NodePosition>> {
  const laidOut = await elk.layout({
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.layered.spacing.nodeNodeBetweenLayers': '60',
      'elk.spacing.nodeNode': '40',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
    },
    children: nodes.map((node) => ({
      id: node.node_key,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    })),
    edges: edges.map((edge, index) => ({
      id: `edge-${index}`,
      sources: [edge.from_node_key],
      targets: [edge.to_node_key],
    })),
  })

  const positions = new Map<string, NodePosition>()
  for (const child of laidOut.children ?? []) {
    positions.set(child.id, { x: child.x ?? 0, y: child.y ?? 0 })
  }
  return positions
}
