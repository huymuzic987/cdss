import { useCallback, useEffect, useRef, useState } from 'react'
import { Tldraw, type Editor, type TLShapeId } from 'tldraw'
import 'tldraw/tldraw.css'
import type { TreeGraphNode, TreeGraphResponse } from '../api/types'
import { layoutTree } from '../layout/elkLayout'
import { buildTreeScene } from './buildTreeScene'
import { DecisionNodeShapeUtil } from './DecisionNodeShapeUtil'

const SHAPE_UTILS = [DecisionNodeShapeUtil]
const HIDDEN_COMPONENTS = {
  Toolbar: null,
  StylePanel: null,
  ActionsMenu: null,
  MainMenu: null,
  PageMenu: null,
  KeyboardShortcutsDialog: null,
  DebugPanel: null,
  DebugMenu: null,
  MenuPanel: null,
  SharePanel: null,
  PeopleMenu: null,
  HelperButtons: null,
  ContextMenu: null,
  QuickActions: null,
}

interface TreeCanvasProps {
  graph: TreeGraphResponse
  focusNodeKey: string | null
  onSelectNode: (node: TreeGraphNode | null) => void
}

export function TreeCanvas({ graph, focusNodeKey, onSelectNode }: TreeCanvasProps) {
  const editorRef = useRef<Editor | null>(null)
  const shapeIdsRef = useRef<Map<string, TLShapeId>>(new Map())
  const [searchQuery, setSearchQuery] = useState('')

  const handleMount = useCallback(
    (editor: Editor) => {
      editorRef.current = editor

      const nodesByKey = new Map(graph.nodes.map((node) => [node.node_key, node]))

      let cancelled = false
      void layoutTree(graph.nodes, graph.edges).then((positions) => {
        if (cancelled) return
        shapeIdsRef.current = buildTreeScene(editor, graph.nodes, graph.edges, positions)

        if (focusNodeKey) {
          const shapeId = shapeIdsRef.current.get(focusNodeKey)
          if (shapeId) {
            editor.select(shapeId)
            editor.zoomToSelection({ animation: { duration: 0 } })
          } else {
            editor.zoomToFit({ animation: { duration: 0 } })
          }
        } else {
          editor.zoomToFit({ animation: { duration: 0 } })
        }
      })

      const unlisten = editor.store.listen(
        () => {
          const selectedIds = editor.getSelectedShapeIds()
          if (selectedIds.length !== 1) {
            onSelectNode(null)
            return
          }
          const shape = editor.getShape(selectedIds[0])
          if (!shape || shape.type !== 'decisionNode') {
            onSelectNode(null)
            return
          }
          const nodeKey = (shape.props as { nodeKey: string }).nodeKey
          onSelectNode(nodesByKey.get(nodeKey) ?? null)
        },
        { source: 'user', scope: 'session' },
      )

      return () => {
        cancelled = true
        unlisten()
      }
    },
    // Runs once per mount; this component is remounted (via `key`) on tab switch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  useEffect(() => {
    if (!focusNodeKey) return
    const editor = editorRef.current
    const shapeId = shapeIdsRef.current.get(focusNodeKey)
    if (!editor || !shapeId) return
    editor.select(shapeId)
    editor.zoomToSelection({ animation: { duration: 200 } })
  }, [focusNodeKey])

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

  return (
    <div className="tree-canvas">
      <div className="canvas-toolbar">
        <input
          type="text"
          placeholder="Search nodes..."
          value={searchQuery}
          onChange={(event) => handleSearch(event.target.value)}
        />
        <button type="button" onClick={() => editorRef.current?.zoomToFit({ animation: { duration: 200 } })}>
          Fit view
        </button>
      </div>
      <Tldraw shapeUtils={SHAPE_UTILS} components={HIDDEN_COMPONENTS} onMount={handleMount} />
    </div>
  )
}
