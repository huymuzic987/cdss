import type { EvaluationResponse, TraversalTraceEntry } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

const TECHNICAL_NODE_TOKENS = new Set([
  'ACTION', 'CHECK', 'COND', 'CONDITION', 'END', 'GLOBAL', 'INF', 'INFERENCE', 'LINK', 'NODE', 'START',
])

export function readableIdentifier(value: string): string {
  const words = value
    .replace(/^T\d+[A-Z]?(?:_|-)/i, '')
    .split(/[_-]+/)
    .filter((word) => word && !TECHNICAL_NODE_TOKENS.has(word.toUpperCase()))
    .map((word) => word.toLowerCase())
  if (words.length === 0) return 'Clinical assessment'
  const text = words.join(' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function readablePathStep(
  entry: TraversalTraceEntry,
  actions: EvaluationResponse['actions'],
  locale: ClinicalDecisionSupportLocale,
): string {
  const action = actions.find((item) => item.tree_key === entry.tree_key && item.node_key === entry.node_key)
  if (action) return locale === 'vi' ? action.text_vi || action.text_en : action.text_en || action.text_vi
  const subject = readableIdentifier(entry.node_key)
  if (entry.node_type === 'START') return locale === 'vi' ? 'Bắt đầu đánh giá lâm sàng' : 'Begin clinical assessment'
  if (entry.node_type === 'CONDITION') return locale === 'vi' ? `Đánh giá: ${subject}` : `Assess: ${subject}`
  if (entry.node_type === 'INFERENCE') return locale === 'vi' ? `Xác định: ${subject}` : `Determine: ${subject}`
  if (entry.node_type === 'LINK') return locale === 'vi' ? `Tiếp tục đánh giá: ${subject}` : `Continue assessment: ${subject}`
  return subject
}
