import { BaseBoxShapeUtil, HTMLContainer, T, type RecordProps, type TLBaseShape } from 'tldraw'
import type { NodeType } from '../api/types'

export interface DecisionNodeShapeProps {
  w: number
  h: number
  nodeKey: string
  nodeType: NodeType
  label: string
  highlightStatus: 'none' | 'entered' | 'active'
  dimmed: boolean
  theme: 'dark' | 'light'
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
    dimmed: T.boolean,
    theme: T.literalEnum('dark', 'light'),
  }

  override getDefaultProps(): DecisionNodeShape['props'] {
    return { w: 220, h: 72, nodeKey: '', nodeType: 'ACTION', label: '', highlightStatus: 'none', dimmed: false, theme: 'dark' }
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

  override indicator(_shape: DecisionNodeShape) {
    return null
  }

  override getIndicatorPath(_shape: DecisionNodeShape) {
    return new Path2D()
  }

  override hideSelectionBoundsFg(_shape: DecisionNodeShape): boolean {
    return true
  }

  override hideSelectionBoundsBg(_shape: DecisionNodeShape): boolean {
    return true
  }

  override component(shape: DecisionNodeShape) {
    const colors = NODE_TYPE_COLORS[shape.props.nodeType]
    const { highlightStatus, dimmed, theme } = shape.props
    const isLight = theme === 'light'

    let borderColor = colors.border
    let borderWidth = 2
    let boxShadow = 'none'
    let transform = 'none'
    let background = isLight ? `${colors.border}22` : colors.background
    let opacity = 1

    if (highlightStatus === 'active') {
      borderWidth = 4
      boxShadow = `0 0 0 4px #000000, 0 0 0 10px ${colors.border}, 0 0 35px 15px ${colors.border}cc`
      transform = 'scale(1.08)'
    } else if (highlightStatus === 'entered') {
      borderWidth = 2
      boxShadow = `0 0 0 4px ${colors.border}, 0 0 20px 8px ${colors.border}80`
      transform = 'scale(1.03)'
    }

    if (dimmed) {
      opacity = 0.35
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
          opacity,
          transition: 'box-shadow 0.2s ease, transform 0.15s ease, border-color 0.2s ease, opacity 0.2s ease',
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.4,
            color: isLight ? '#000000' : highlightStatus !== 'none' ? borderColor : colors.border,
            textTransform: 'uppercase',
          }}
        >
          {shape.props.nodeType}
        </div>
        <div
          style={{
            fontSize: 13,
            color: isLight ? '#000000' : '#f8fafc',
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
