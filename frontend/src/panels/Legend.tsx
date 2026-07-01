import { NODE_TYPE_COLORS } from '../canvas/DecisionNodeShapeUtil'
import type { NodeType } from '../api/types'

const CANVAS_NODE_TYPES: NodeType[] = ['START', 'CONDITION', 'INFERENCE', 'ACTION', 'END', 'LINK']

export function Legend() {
  return (
    <div className="panel legend">
      {CANVAS_NODE_TYPES.map((nodeType) => {
        const colors = NODE_TYPE_COLORS[nodeType]
        return (
          <div key={nodeType} className="legend-item">
            <span
              className="legend-swatch"
              style={{ background: colors.background, border: `2px solid ${colors.border}` }}
            />
            <span>{nodeType}</span>
          </div>
        )
      })}
    </div>
  )
}
