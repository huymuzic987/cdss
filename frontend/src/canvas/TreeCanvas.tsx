import { useCallback, useEffect, useRef, useState } from 'react'
import { Tldraw, type Editor, type TLShapeId } from 'tldraw'
import 'tldraw/tldraw.css'
import type { TreeGraphNode, TreeGraphResponse } from '../api/types'
import { layoutTree, type NodePosition } from '../layout/elkLayout'
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
  theme: 'dark' | 'light'
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

export function TreeCanvas({
  graph,
  theme,
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

  const [arrowKind, setArrowKind] = useState<'straight' | 'elbow'>(() => {
    const savedLayoutStr = localStorage.getItem(`cdss-tree-layout-${graph.tree.tree_key}`)
    if (savedLayoutStr) {
      try {
        const parsed = JSON.parse(savedLayoutStr)
        if (parsed.arrowKind === 'elbow' || parsed.arrowKind === 'straight') {
          return parsed.arrowKind
        }
      } catch {}
    }
    return 'straight'
  })

  const arrowKindRef = useRef(arrowKind)
  useEffect(() => {
    arrowKindRef.current = arrowKind
  }, [arrowKind])

  const onSelectNodeRef = useRef(onSelectNode)
  useEffect(() => {
    onSelectNodeRef.current = onSelectNode
  }, [onSelectNode])

  const isSceneLoadedRef = useRef(false)
  const lastSavedPositionsRef = useRef<Record<string, { x: number; y: number }>>({})

  const handleMount = useCallback(
    (editor: Editor) => {
      editorRef.current = editor
      editor.user.updateUserPreferences({ colorScheme: theme })

      const nodesByKey = new Map(graph.nodes.map((node) => [node.node_key, node]))

      // Retrieve saved configuration from localStorage on mount
      let savedPositions: Record<string, { x: number; y: number }> | null = null
      let savedArrowKind: 'straight' | 'elbow' = 'straight'
      const savedLayoutStr = localStorage.getItem(`cdss-tree-layout-${graph.tree.tree_key}`)
      if (savedLayoutStr) {
        try {
          const parsed = JSON.parse(savedLayoutStr)
          if (parsed.positions) savedPositions = parsed.positions
          if (parsed.arrowKind) savedArrowKind = parsed.arrowKind
        } catch (e) {
          console.error('Failed to parse saved layout', e)
        }
      }

      let cancelled = false
      void layoutTree(graph.nodes, graph.edges).then((positions) => {
        if (cancelled) return

        // Merge calculated ELK layout with saved positions
        const mergedPositions = new Map<string, NodePosition>()
        for (const [nodeKey, pos] of positions.entries()) {
          const savedPos = savedPositions?.[nodeKey]
          if (savedPos) {
            mergedPositions.set(nodeKey, savedPos)
          } else {
            mergedPositions.set(nodeKey, pos)
          }
        }

        shapeIdsRef.current = buildTreeScene(editor, graph.nodes, graph.edges, mergedPositions, savedArrowKind, theme)

        if (focusNodeKey) {
          const shapeId = shapeIdsRef.current.get(focusNodeKey)
          if (shapeId) {
            editor.select(shapeId)
          }
        }
        editor.zoomToFit({ animation: { duration: 0 } })

        // Initialize lastSavedPositionsRef with whatever was rendered
        const initialPositions: Record<string, { x: number; y: number }> = {}
        const initialNodes = editor.getCurrentPageShapes().filter((s) => s.type === 'decisionNode')
        for (const shape of initialNodes) {
          const nodeKey = (shape.props as any).nodeKey
          if (nodeKey) {
            initialPositions[nodeKey] = { x: shape.x, y: shape.y }
          }
        }
        lastSavedPositionsRef.current = initialPositions

        isSceneLoadedRef.current = true
        setIsSceneLoaded(true)
      })

      const unlisten = editor.store.listen(
        () => {
          // Node selection logic
          const selectedIds = editor.getSelectedShapeIds()
          if (selectedIds.length !== 1) {
            onSelectNodeRef.current(null)
          } else {
            const shape = editor.getShape(selectedIds[0])
            if (shape && shape.type === 'decisionNode') {
              const nodeKey = (shape.props as { nodeKey: string }).nodeKey
              onSelectNodeRef.current(nodesByKey.get(nodeKey) ?? null)
            } else {
              onSelectNodeRef.current(null)
            }
          }

          // Node persistence logic
          if (!isSceneLoadedRef.current) return

          const nodes = editor.getCurrentPageShapes().filter((s) => s.type === 'decisionNode')
          let hasMoved = false
          const currentPositions: Record<string, { x: number; y: number }> = {}

          for (const shape of nodes) {
            const nodeKey = (shape.props as any).nodeKey
            if (nodeKey) {
              currentPositions[nodeKey] = { x: shape.x, y: shape.y }
              const lastPos = lastSavedPositionsRef.current[nodeKey]
              if (!lastPos || lastPos.x !== shape.x || lastPos.y !== shape.y) {
                hasMoved = true
              }
            }
          }

          if (hasMoved) {
            lastSavedPositionsRef.current = currentPositions
            localStorage.setItem(
              `cdss-tree-layout-${graph.tree.tree_key}`,
              JSON.stringify({ positions: currentPositions, arrowKind: arrowKindRef.current }),
            )
          }
        },
        { source: 'user', scope: 'session' },
      )

      return () => {
        cancelled = true
        unlisten()
        isSceneLoadedRef.current = false
      }
    },
    // Runs once per mount; this component is remounted (via `key`) on tab switch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  // Keep tldraw's internal color scheme in sync with the app theme toggle
  useEffect(() => {
    editorRef.current?.user.updateUserPreferences({ colorScheme: theme })
  }, [theme])

  // Keep node shape colors in sync with the app theme toggle
  useEffect(() => {
    const editor = editorRef.current
    if (!editor || !isSceneLoaded) return

    for (const shapeId of shapeIdsRef.current.values()) {
      const shape = editor.getShape(shapeId)
      if (shape && shape.type === 'decisionNode' && (shape.props as { theme: string }).theme !== theme) {
        editor.updateShape({ id: shapeId, type: 'decisionNode', props: { theme } })
      }
    }
  }, [theme, isSceneLoaded])

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

  const handleChangeArrowKind = (kind: 'straight' | 'elbow') => {
    setArrowKind(kind)
    const editor = editorRef.current
    if (editor) {
      updateArrowShapes(editor, kind)
    }

    const savedLayoutStr = localStorage.getItem(`cdss-tree-layout-${graph.tree.tree_key}`)
    let positions: Record<string, { x: number; y: number }> = {}
    if (savedLayoutStr) {
      try {
        positions = JSON.parse(savedLayoutStr).positions || {}
      } catch {}
    }
    if (Object.keys(positions).length === 0 && editor) {
      const nodes = editor.getCurrentPageShapes().filter((s) => s.type === 'decisionNode')
      for (const shape of nodes) {
        const nodeKey = (shape.props as any).nodeKey
        if (nodeKey) {
          positions[nodeKey] = { x: shape.x, y: shape.y }
        }
      }
    }
    localStorage.setItem(
      `cdss-tree-layout-${graph.tree.tree_key}`,
      JSON.stringify({ positions, arrowKind: kind }),
    )
  }

  const handleResetLayout = async () => {
    const editor = editorRef.current
    if (!editor) return

    localStorage.removeItem(`cdss-tree-layout-${graph.tree.tree_key}`)
    setArrowKind('straight')

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

    // Update arrows in-place to straight
    updateArrowShapes(editor, 'straight')

    // Clear last saved positions cache to match defaults
    lastSavedPositionsRef.current = {}

    // Zoom to fit
    editor.zoomToFit({ animation: { duration: 200 } })
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
        <button
          type="button"
          className={arrowKind === 'straight' ? 'active' : ''}
          onClick={() => handleChangeArrowKind('straight')}
        >
          Straight
        </button>
        <button
          type="button"
          className={arrowKind === 'elbow' ? 'active' : ''}
          onClick={() => handleChangeArrowKind('elbow')}
        >
          Elbow
        </button>
        <button type="button" onClick={handleResetLayout}>
          Reset layout
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
