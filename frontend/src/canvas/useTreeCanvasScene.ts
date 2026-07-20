import { useCallback, useEffect, useRef, useState } from 'react'
import type { Editor, TLShapeId } from 'tldraw'
import type { TreeGraphNode, TreeGraphResponse } from '../api/types'
import { layoutTree, type NodePosition } from '../layout/elkLayout'
import { buildTreeScene } from './buildTreeScene'

interface UseTreeCanvasSceneOptions {
  graph: TreeGraphResponse
  theme: 'dark' | 'light'
  focusNodeKey: string | null
  onSelectNode: (node: TreeGraphNode | null) => void
}

/** Mounts the tldraw editor, lays out the tree, and persists node positions
 * (and arrow style) to localStorage as the user drags nodes around. */
export function useTreeCanvasScene({ graph, theme, focusNodeKey, onSelectNode }: UseTreeCanvasSceneOptions) {
  const editorRef = useRef<Editor | null>(null)
  const shapeIdsRef = useRef<Map<string, TLShapeId>>(new Map())
  const [isSceneLoaded, setIsSceneLoaded] = useState(false)
  const [arrowKind, setArrowKind] = useState<'straight' | 'elbow'>('elbow')

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
      let savedArrowKind: 'straight' | 'elbow' = 'elbow'
      const savedLayoutStr = localStorage.getItem(`cdss-tree-layout-${graph.tree.tree_key}`)
      if (savedLayoutStr) {
        try {
          const parsed = JSON.parse(savedLayoutStr)
          if (parsed.positions) savedPositions = parsed.positions
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

  return { editorRef, shapeIdsRef, lastSavedPositionsRef, isSceneLoaded, arrowKind, setArrowKind, handleMount }
}
