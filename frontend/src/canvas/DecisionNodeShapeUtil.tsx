import { BaseBoxShapeUtil, HTMLContainer, T, type RecordProps, type TLBaseShape } from 'tldraw'
import type { NodeType } from '../api/types'

export interface DecisionNodeShapeProps {
  w: number
  h: number
  nodeKey: string
  nodeType: NodeType
  label: string
  highlightStatus: 'none' | 'entered' | 'active'
}

export type DecisionNodeShape = TLBaseShape<'decisionNode', DecisionNodeShapeProps>

declare module 'tldraw' {
  interface TLGlobalShapePropsMap {
    decisionNode: DecisionNodeShapeProps
  }
}

export const NODE_TYPE_COLORS: Record<NodeType, { background: string; border: string }> = {
  START: { background: '#071d12', border: '#10b981' },
  CONDITION: { background: '#1c1704', border: '#eab308' },
  INFERENCE: { background: '#0a162e', border: '#3b82f6' },
  ACTION: { background: '#1d0e07', border: '#f97316' },
  END: { background: '#140822', border: '#a855f7' },
  LINK: { background: '#1a0611', border: '#ec4899' },
  GLOBAL: { background: '#111827', border: '#6b7280' },
}

export class DecisionNodeShapeUtil extends BaseBoxShapeUtil<DecisionNodeShape> {
  static override type = 'decisionNode' as const

  static override props: RecordProps<DecisionNodeShape> = {
    w: T.number,
    h: T.number,
    nodeKey: T.string,
    nodeType: T.literalEnum(
      'START',
      'CONDITION',
      'INFERENCE',
      'ACTION',
      'END',
      'LINK',
      'GLOBAL',
    ),
    label: T.string,
    highlightStatus: T.literalEnum('none', 'entered', 'active'),
  }

  override getDefaultProps(): DecisionNodeShape['props'] {
    return { w: 220, h: 72, nodeKey: '', nodeType: 'ACTION', label: '', highlightStatus: 'none' }
  }

  override canEdit(): boolean {
    return false
  }

  override canResize(): boolean {
    return false
  }

  override hideResizeHandles(): boolean {
    return true
  }

  override hideRotateHandle(): boolean {
    return true
  }

  override getIndicatorPath(shape: DecisionNodeShape) {
    const path = new Path2D()
    path.rect(0, 0, shape.props.w, shape.props.h)
    return path
  }

  override component(shape: DecisionNodeShape) {
    const colors = NODE_TYPE_COLORS[shape.props.nodeType]
    const { highlightStatus } = shape.props

    let borderColor = colors.border
    let borderWidth = 2
    let boxShadow = 'none'
    let transform = 'none'
    let background = colors.background

    if (highlightStatus === 'active') {
      borderColor = '#00f0ff'
      borderWidth = 3
      boxShadow = '0 0 0 3px rgba(0, 240, 255, 0.4), 0 0 18px 6px rgba(0, 240, 255, 0.3)'
      transform = 'scale(1.04)'
      background = '#092533'
    } else if (highlightStatus === 'entered') {
      borderColor = '#0ea5e9'
      borderWidth = 3
      boxShadow = '0 0 0 2px rgba(14, 165, 233, 0.3), 0 0 12px 3px rgba(14, 165, 233, 0.2)'
      background = '#071824'
    }

    return (
      <HTMLContainer
        style={{
          width: shape.props.w,
          height: shape.props.h,
          background,
          border: `${borderWidth}px solid ${borderColor}`,
          borderRadius: 8,
          padding: '6px 10px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 4,
          pointerEvents: 'all',
          fontFamily: 'system-ui, sans-serif',
          boxSizing: 'border-box',
          overflow: 'hidden',
          boxShadow,
          transform,
          transition: 'box-shadow 0.2s ease, transform 0.15s ease, border-color 0.2s ease',
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.4,
            color: highlightStatus !== 'none' ? borderColor : colors.border,
            textTransform: 'uppercase',
          }}
        >
          {shape.props.nodeType}
        </div>
        <div
          style={{
            fontSize: 13,
            color: '#f8fafc',
            lineHeight: 1.3,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {shape.props.label}
        </div>
      </HTMLContainer>
    )
  }
}
