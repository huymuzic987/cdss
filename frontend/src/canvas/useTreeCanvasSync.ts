import { useEffect } from 'react'
import type { Editor, TLShapeId } from 'tldraw'

interface UseTreeCanvasSyncOptions {
  editorRef: React.RefObject<Editor | null>
  shapeIdsRef: React.RefObject<Map<string, TLShapeId>>
  isSceneLoaded: boolean
  theme: 'dark' | 'light'
  focusNodeKey: string | null
  highlightedNodeKeys?: ReadonlySet<string>
  activeNodeKey?: string | null
}

/** Keeps the mounted tldraw scene in sync with reactive props: theme, focus,
 * traversal highlights, and pan/zoom onto the active node. */
export function useTreeCanvasSync({
  editorRef,
  shapeIdsRef,
  isSceneLoaded,
  theme,
  focusNodeKey,
  highlightedNodeKeys,
  activeNodeKey,
}: UseTreeCanvasSyncOptions) {
  // Keep tldraw's internal color scheme in sync with the app theme toggle
  useEffect(() => {
    editorRef.current?.user.updateUserPreferences({ colorScheme: theme })
  }, [editorRef, theme])

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
  }, [editorRef, shapeIdsRef, theme, isSceneLoaded])

  // Focus / pan to node when focusNodeKey changes
  useEffect(() => {
    if (!focusNodeKey || !isSceneLoaded) return
    const editor = editorRef.current
    const shapeId = shapeIdsRef.current.get(focusNodeKey)
    if (!editor || !shapeId) return
    editor.select(shapeId)
    editor.zoomToFit({ animation: { duration: 200 } })
  }, [editorRef, shapeIdsRef, focusNodeKey, isSceneLoaded])

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
  }, [editorRef, shapeIdsRef, highlightedNodeKeys, activeNodeKey, isSceneLoaded])

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
  }, [editorRef, shapeIdsRef, activeNodeKey, isSceneLoaded])
}
