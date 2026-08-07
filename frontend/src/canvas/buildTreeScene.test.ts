import type { Editor } from 'tldraw'
import { describe, expect, it, vi } from 'vitest'
import type { TreeEdgeLayout, TreeGraphEdge, TreeGraphNode } from '../api/types'
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
  const bindings: Record<string, unknown>[] = []
  const editor = {
    createShape: vi.fn((shape: unknown) => {
      shapes.push(shape as Record<string, unknown>)
    }),
    createBindings: vi.fn((createdBindings: unknown[]) => {
      bindings.push(...(createdBindings as Record<string, unknown>[]))
    }),
  } as unknown as Editor
  return { editor, shapes, bindings }
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
      x: 210,
      y: 272,
      props: {
        start: { x: 0, y: 0 },
        end: { x: 200, y: 128 },
      },
    })
  })

  it('rebuilds geometry and anchors when saved endpoints are stale', () => {
    const { editor, shapes, bindings } = createEditorSpy()

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
      {
        'from->to': {
          x: 500,
          y: 500,
          bend: 18,
          elbowMidPoint: 0.25,
          start: { x: 699, y: 299 },
          end: { x: 399, y: 99 },
          start_anchor: { x: 0, y: 0.5 },
          end_anchor: { x: 1, y: 0.5 },
        },
      },
    )

    expect(shapes[2]).toMatchObject({
      type: 'arrow',
      x: 210,
      y: 272,
      props: {
        bend: 0,
        start: { x: 0, y: 0 },
        end: { x: 200, y: 128 },
      },
    })
    expect(bindings).toMatchObject([
      expect.objectContaining({
        props: expect.objectContaining({ terminal: 'start', normalizedAnchor: { x: 0.5, y: 1 } }),
      }),
      expect.objectContaining({
        props: expect.objectContaining({ terminal: 'end', normalizedAnchor: { x: 0.5, y: 0 } }),
      }),
    ])
  })
})
