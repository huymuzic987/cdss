import { BaseBoxShapeUtil, HTMLContainer, T, type RecordProps, type TLBaseShape } from 'tldraw'
import type { NodeType } from '../api/types'

export interface DecisionNodeShapeProps {
  w: number
  h: number
  nodeKey: string
  nodeType: NodeType
  label: string
}

export type DecisionNodeShape = TLBaseShape<'decisionNode', DecisionNodeShapeProps>

declare module 'tldraw' {
  interface TLGlobalShapePropsMap {
    decisionNode: DecisionNodeShapeProps
  }
}

export const NODE_TYPE_COLORS: Record<NodeType, { background: string; border: string }> = {
  START: { background: '#dcfce7', border: '#16a34a' },
  CONDITION: { background: '#fef9c3', border: '#ca8a04' },
  INFERENCE: { background: '#dbeafe', border: '#2563eb' },
  ACTION: { background: '#ede9fe', border: '#7c3aed' },
  END: { background: '#fee2e2', border: '#dc2626' },
  LINK: { background: '#cffafe', border: '#0891b2' },
  GLOBAL: { background: '#e5e7eb', border: '#4b5563' },
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
  }

  override getDefaultProps(): DecisionNodeShape['props'] {
    return { w: 220, h: 72, nodeKey: '', nodeType: 'ACTION', label: '' }
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
    return (
      <HTMLContainer
        style={{
          width: shape.props.w,
          height: shape.props.h,
          background: colors.background,
          border: `2px solid ${colors.border}`,
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
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.4,
            color: colors.border,
            textTransform: 'uppercase',
          }}
        >
          {shape.props.nodeType}
        </div>
        <div
          style={{
            fontSize: 13,
            color: '#111827',
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
