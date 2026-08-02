import type { EvaluationResponse, ExecutedAction, TreeGraphResponse } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { readableIdentifier } from './decisionPath'
import type { OrderProvenance } from './RecommendedOrderCard'

export function buildOrderProvenance(
  action: ExecutedAction | undefined,
  references: EvaluationResponse['references'],
  graphs: Record<string, TreeGraphResponse>,
  locale: ClinicalDecisionSupportLocale,
): OrderProvenance {
  if (!action) {
    return { nodeLabel: 'Clinical recommendation', nodeKey: 'N/A', treeName: 'CDSS', references: [] }
  }
  const graph = graphs[action.tree_key]
  const node = graph?.nodes.find((item) => item.node_key === action.node_key)
  const nodeLabel = locale === 'vi'
    ? node?.text_vi || action.text_vi || node?.text_en || action.text_en
    : node?.text_en || action.text_en || node?.text_vi || action.text_vi
  const treeName = graph
    ? (locale === 'vi' ? graph.tree.name_vi || graph.tree.name_en : graph.tree.name_en || graph.tree.name_vi)
    : readableIdentifier(action.tree_key)
  return {
    nodeLabel,
    nodeKey: action.node_key,
    treeName,
    references: references.filter(
      (reference) => reference.tree_key === action.tree_key && reference.node_key === action.node_key,
    ),
  }
}
