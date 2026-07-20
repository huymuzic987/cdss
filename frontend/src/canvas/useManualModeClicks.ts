import { useRef } from 'react'

/** During manual traversal, intercepts plain left-clicks on the canvas
 * (as opposed to drags, or clicks on the toolbar / with modifier keys)
 * to advance to the next step. */
export function useManualModeClicks(manualMode: boolean | undefined, onCanvasClick: (() => void) | undefined) {
  const dragStartRef = useRef<{ x: number; y: number } | null>(null)

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

  return { handlePointerDownCapture, handlePointerUpCapture, handleClickCapture }
}
