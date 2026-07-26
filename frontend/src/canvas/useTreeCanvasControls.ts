import { useState } from 'react'
import type { Editor, TLShapeId } from 'tldraw'
import { resetTreeLayout, saveTreeLayout } from '../api/client'
import type { TreeGraphResponse } from '../api/types'
import { layoutTree } from '../layout/elkLayout'

function updateArrowShapes(editor: Editor, kind: 'straight' | 'elbow') {
  const arrowShapes = editor.getCurrentPageShapes().filter((s) => s.type === 'arrow')
  editor.updateShapes(
    arrowShapes.map((shape) => ({
      id: shape.id,
      type: 'arrow',
      props: {
        kind: kind === 'elbow' ? 'elbow' : 'arc',
        bend: kind === 'straight' ? 0 : shape.props.bend,
      },
    })),
  )
}

function currentNodePositions(editor: Editor): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {}
  const nodes = editor.getCurrentPageShapes().filter((s) => s.type === 'decisionNode')
  for (const shape of nodes) {
    const nodeKey = (shape.props as any).nodeKey
    if (nodeKey) {
      positions[nodeKey] = { x: shape.x, y: shape.y }
    }
  }
  return positions
}

interface UseTreeCanvasControlsOptions {
  editorRef: React.RefObject<Editor | null>
  shapeIdsRef: React.RefObject<Map<string, TLShapeId>>
  lastSavedPositionsRef: React.RefObject<Record<string, { x: number; y: number }>>
  lastSavedArrowKindRef: React.RefObject<'straight' | 'elbow'>
  graph: TreeGraphResponse
  setArrowKind: (kind: 'straight' | 'elbow') => void
}

/** Toolbar behaviors: node search, arrow-style toggle, and resetting the
 * layout back to the ELK-computed default. */
export function useTreeCanvasControls({
  editorRef,
  shapeIdsRef,
  lastSavedPositionsRef,
  lastSavedArrowKindRef,
  graph,
  setArrowKind,
}: UseTreeCanvasControlsOptions) {
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    const editor = editorRef.current
    const trimmed = query.trim().toLowerCase()
    if (!editor || !trimmed) return

    const match = graph.nodes.find(
      (node) =>
          node.node_key.toLowerCase().includes(trimmed) ||
          node.text_en.toLowerCase().includes(trimmed),
    )
    const shapeId = match && shapeIdsRef.current.get(match.node_key)
    if (!shapeId) return
    editor.select(shapeId)
    editor.zoomToSelection({ animation: { duration: 200 } })
  }

  const handleChangeArrowKind = (kind: 'straight' | 'elbow') => {
    setArrowKind(kind)
    lastSavedArrowKindRef.current = kind
    const editor = editorRef.current
    if (editor) {
      updateArrowShapes(editor, kind)
    }

    const positions = editor ? currentNodePositions(editor) : {}
    void saveTreeLayout(graph.tree.tree_key, { positions, arrow_kind: kind }).catch((error) =>
      console.error('Failed to save layout', error),
    )
  }

  const handleResetLayout = async () => {
    const editor = editorRef.current
    if (!editor) return

    void resetTreeLayout(graph.tree.tree_key).catch((error) => console.error('Failed to reset layout', error))
    setArrowKind('elbow')

    // Run ELK layout
    const elkPositions = await layoutTree(graph.nodes, graph.edges)

    // Update nodes in-place
    const nodeShapes = editor.getCurrentPageShapes().filter((s) => s.type === 'decisionNode')
    editor.updateShapes(
      nodeShapes.map((shape) => {
        const nodeKey = (shape.props as any).nodeKey
        const pos = elkPositions.get(nodeKey) ?? { x: shape.x, y: shape.y }
        return {
          id: shape.id,
          type: 'decisionNode',
          x: pos.x,
          y: pos.y,
        }
      }),
    )

    // Update arrows in-place to elbow
    updateArrowShapes(editor, 'elbow')

    // Clear last saved positions and arrow kind cache to match defaults
    lastSavedPositionsRef.current = {}
    lastSavedArrowKindRef.current = 'elbow'

    // Zoom to fit
    editor.zoomToFit({ animation: { duration: 200 } })
  }

  return { searchQuery, handleSearch, handleChangeArrowKind, handleResetLayout }
}

