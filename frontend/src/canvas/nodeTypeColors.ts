import type { NodeType } from '../api/types'

type NodeTypeColors = { background: string; border: string }

export const NODE_TYPE_COLORS: Record<NodeType, NodeTypeColors> = {
  START: { background: '#071d12', border: '#10b981' },
  CONDITION: { background: '#1c1704', border: '#eab308' },
  INFERENCE: { background: '#0a162e', border: '#3b82f6' },
  ACTION: { background: '#1d0e07', border: '#f97316' },
  END: { background: '#140822', border: '#a855f7' },
  LINK: { background: '#1a0611', border: '#ec4899' },
  GLOBAL: { background: '#111827', border: '#6b7280' },
}

// Near-black, fully saturated borders + bold fills keep node types unmistakable against a light canvas.
export const NODE_TYPE_COLORS_LIGHT: Record<NodeType, NodeTypeColors> = {
  START: { background: '#6ee7b7', border: '#064e3b' },
  CONDITION: { background: '#fcd34d', border: '#78350f' },
  INFERENCE: { background: '#93c5fd', border: '#1e3a8a' },
  ACTION: { background: '#fdba74', border: '#7c2d12' },
  END: { background: '#d8b4fe', border: '#581c87' },
  LINK: { background: '#f9a8d4', border: '#831843' },
  GLOBAL: { background: '#9ca3af', border: '#111827' },
}

export function getNodeTypeColors(nodeType: NodeType, theme: 'dark' | 'light') {
  return theme === 'light' ? NODE_TYPE_COLORS_LIGHT[nodeType] : NODE_TYPE_COLORS[nodeType]
}
