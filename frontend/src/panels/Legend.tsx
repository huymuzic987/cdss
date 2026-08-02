import { getNodeTypeColors } from '../canvas/nodeTypeColors'
import type { NodeType } from '../api/types'

const CANVAS_NODE_TYPES: NodeType[] = ['START', 'CONDITION', 'INFERENCE', 'ACTION', 'END', 'LINK', 'GLOBAL']

export function Legend({ theme }: { theme: 'dark' | 'light' }) {
  return (
    <div className="panel legend">
      {CANVAS_NODE_TYPES.map((nodeType) => {
        const colors = getNodeTypeColors(nodeType, theme)
        return (
          <div key={nodeType} className="legend-item">
            <span
              className="legend-swatch"
              style={{
                background: colors.background,
                border: `2px solid ${colors.border}`,
              }}
            />
            <span>{nodeType}</span>
          </div>
        )
      })}
    </div>
  )
}
