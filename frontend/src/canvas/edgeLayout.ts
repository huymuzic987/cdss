import type { Editor } from 'tldraw'
import type { TreeEdgeLayout } from '../api/types'

/** Capture geometry by graph edge identity, never by tldraw's transient shape id. */
export function currentEdgeLayouts(editor: Editor): Record<string, TreeEdgeLayout> {
  const layouts: Record<string, TreeEdgeLayout> = {}
  const arrows = editor.getCurrentPageShapes().filter((shape) => shape.type === 'arrow')

  for (const shape of arrows) {
    const edgeKey = (shape.meta as { edgeKey?: string }).edgeKey
    if (!edgeKey) continue
    const props = shape.props as any
    const bindings = editor.getBindingsFromShape(shape.id, 'arrow') as any[]
    const startBinding = bindings.find((binding) => binding.props?.terminal === 'start')
    const endBinding = bindings.find((binding) => binding.props?.terminal === 'end')
    layouts[edgeKey] = {
      x: shape.x,
      y: shape.y,
      bend: props.bend,
      elbowMidPoint: props.elbowMidPoint,
      start: props.start,
      end: props.end,
      start_anchor: startBinding?.props?.normalizedAnchor,
      end_anchor: endBinding?.props?.normalizedAnchor,
    }
  }
  return layouts
}
