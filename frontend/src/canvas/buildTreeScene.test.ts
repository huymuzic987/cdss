import type { Editor } from 'tldraw'
import { describe, expect, it, vi } from 'vitest'
import type { TreeEdgeLayout, TreeGraphEdge, TreeGraphNode } from '../api/types'
import { NODE_HEIGHT, NODE_WIDTH } from '../layout/nodeDimensions'
import { buildTreeScene } from './buildTreeScene'

function node(nodeKey: string, displayOrder: number): TreeGraphNode {
  return {
    node_key: nodeKey,
    node_type: 'CONDITION',
    text_en: nodeKey,
    text_vi: nodeKey,
    condition_definition: null,
    context_patch: null,
    action_payload: null,
    link_target_tree_key: null,
    link_target_node_key: null,
    display_order: displayOrder,
  }
}

function edge(from_node_key: string, to_node_key: string): TreeGraphEdge {
  return { from_node_key, to_node_key, traversal_order: 1 }
}

function createEditorSpy() {
  const shapes: Record<string, unknown>[] = []
  const editor = {
    createShape: vi.fn((shape: unknown) => {
      shapes.push(shape as Record<string, unknown>)
    }),
    createBindings: vi.fn(),
  } as unknown as Editor
  return { editor, shapes }
}

describe('buildTreeScene', () => {
  it('creates visible default geometry for edges without a bound saved layout', () => {
    const { editor, shapes } = createEditorSpy()
    const edgeKey = 'from->to'
    const staleLayout: TreeEdgeLayout = {
      x: 500,
      y: 500,
      bend: 0,
      elbowMidPoint: 0.5,
      start: { x: 1, y: 1 },
      end: { x: 2, y: 2 },
    }

    buildTreeScene(
      editor,
      [node('from', 1), node('to', 2)],
      [edge('from', 'to')],
      new Map([
        ['from', { x: 100, y: 200 }],
        ['to', { x: 300, y: 400 }],
      ]),
      'elbow',
      'dark',
      { [edgeKey]: staleLayout },
    )

    expect(shapes[2]).toMatchObject({
      type: 'arrow',
      x: 0,
      y: 0,
      props: {
        start: { x: 100 + NODE_WIDTH / 2, y: 200 + NODE_HEIGHT },
        end: { x: 300 + NODE_WIDTH / 2, y: 400 },
      },
    })
  })
})
