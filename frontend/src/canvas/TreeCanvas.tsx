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
  SelectionBackground: null,
  SelectionForeground: null,
  SelectionOutline: null,
}

interface TreeCanvasProps {
  graph: TreeGraphResponse
  focusNodeKey: string | null
  onSelectNode: (node: TreeGraphNode | null) => void
  /** Node keys that were traversed (entered) */
  highlightedNodeKeys?: ReadonlySet<string>
  /** The currently active node being stepped through */
  activeNodeKey?: string | null
  /** When true, an overlay awaits a click to reveal the next manual-traversal step */
  manualMode?: boolean
  manualStepInfo?: { current: number; total: number } | null
  onCanvasClick?: () => void
}

export function TreeCanvas({
  graph,
  focusNodeKey,
  onSelectNode,
  highlightedNodeKeys,
  activeNodeKey,
  manualMode,
  manualStepInfo,
  onCanvasClick,
}: TreeCanvasProps) {
  const editorRef = useRef<Editor | null>(null)
  const shapeIdsRef = useRef<Map<string, TLShapeId>>(new Map())
  const dragStartRef = useRef<{ x: number; y: number } | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isSceneLoaded, setIsSceneLoaded] = useState(false)

  const handleMount = useCallback(
    (editor: Editor) => {
      editorRef.current = editor
      editor.user.updateUserPreferences({ colorScheme: 'dark' })

      const nodesByKey = new Map(graph.nodes.map((node) => [node.node_key, node]))

      let cancelled = false
      void layoutTree(graph.nodes, graph.edges).then((positions) => {
        if (cancelled) return
        shapeIdsRef.current = buildTreeScene(editor, graph.nodes, graph.edges, positions)

        if (focusNodeKey) {
          const shapeId = shapeIdsRef.current.get(focusNodeKey)
          if (shapeId) {
            editor.select(shapeId)
          }
        }
        editor.zoomToFit({ animation: { duration: 0 } })
        setIsSceneLoaded(true)
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

  // Focus / pan to node when focusNodeKey changes
  useEffect(() => {
    if (!focusNodeKey || !isSceneLoaded) return
    const editor = editorRef.current
    const shapeId = shapeIdsRef.current.get(focusNodeKey)
    if (!editor || !shapeId) return
    editor.select(shapeId)
    editor.zoomToFit({ animation: { duration: 200 } })
  }, [focusNodeKey, isSceneLoaded])

  // Apply highlight status to shapes when highlight sets change
  useEffect(() => {
    const editor = editorRef.current
    if (!editor || !isSceneLoaded) return

    const hasAnyHighlight = (highlightedNodeKeys && highlightedNodeKeys.size > 0) || !!activeNodeKey

    for (const [nodeKey, shapeId] of shapeIdsRef.current) {
      let status: 'none' | 'entered' | 'active' = 'none'
      if (activeNodeKey && nodeKey === activeNodeKey) {
        status = 'active'
      } else if (highlightedNodeKeys?.has(nodeKey)) {
        status = 'entered'
      }
      const isDimmed = hasAnyHighlight && status === 'none'

      const shape = editor.getShape(shapeId)
      if (shape && shape.type === 'decisionNode') {
        const currentProps = shape.props as { highlightStatus: string; dimmed?: boolean }
        const currentStatus = currentProps.highlightStatus
        const currentDimmed = !!currentProps.dimmed

        if (currentStatus !== status || currentDimmed !== isDimmed) {
          editor.updateShape({
            id: shapeId,
            type: 'decisionNode',
            props: { highlightStatus: status, dimmed: isDimmed },
          })
        }
      }
    }
  }, [highlightedNodeKeys, activeNodeKey, isSceneLoaded])

  // Pan / zoom to the active node during traversal
  useEffect(() => {
    if (!activeNodeKey || !isSceneLoaded) return
    const editor = editorRef.current
    const shapeId = shapeIdsRef.current.get(activeNodeKey)
    if (!editor || !shapeId) return
    editor.zoomToSelection({ animation: { duration: 300 } })
    // Don't select — that fires onSelectNode which would overwrite. Just center.
    const shapeBounds = editor.getShapePageBounds(shapeId)
    if (shapeBounds) {
      editor.centerOnPoint(
        { x: shapeBounds.midX, y: shapeBounds.midY },
        { animation: { duration: 300 } },
      )
    }
  }, [activeNodeKey, isSceneLoaded])

  const handlePointerDownCapture = (e: React.PointerEvent) => {
    if (!manualMode) return
    if (e.button !== 0 || e.ctrlKey || e.shiftKey || e.altKey || e.metaKey) return
    if ((e.target as HTMLElement).closest('.canvas-toolbar')) return

    // Track starting position to differentiate click vs drag
    dragStartRef.current = { x: e.clientX, y: e.clientY }
    e.stopPropagation()
  }

  const handlePointerUpCapture = (e: React.PointerEvent) => {
    if (!manualMode) return
    if (e.button !== 0 || e.ctrlKey || e.shiftKey || e.altKey || e.metaKey) return
    if ((e.target as HTMLElement).closest('.canvas-toolbar')) return

    e.stopPropagation()
  }

  const handleClickCapture = (e: React.MouseEvent) => {
    if (!manualMode) return
    if (e.button !== 0 || e.ctrlKey || e.shiftKey || e.altKey || e.metaKey) return
    if ((e.target as HTMLElement).closest('.canvas-toolbar')) return

    e.stopPropagation()
    e.preventDefault()

    const start = dragStartRef.current
    dragStartRef.current = null

    if (start) {
      const dx = e.clientX - start.x
      const dy = e.clientY - start.y
      const distance = Math.sqrt(dx * dx + dy * dy)
      if (distance > 5) return
    }

    onCanvasClick?.()
  }

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
    <div
      className="tree-canvas"
      onPointerDownCapture={handlePointerDownCapture}
      onPointerUpCapture={handlePointerUpCapture}
      onClickCapture={handleClickCapture}
    >
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
      {manualMode && (
        <div className="manual-overlay">
          {manualStepInfo && (
            <div className="manual-banner">
              <span className="manual-pulse-dot" />
              <span>
                Manual Traverse: Click canvas to advance (Step{' '}
                <strong>{manualStepInfo.current}</strong> of{' '}
                <strong>{manualStepInfo.total}</strong>)
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
