import { describe, expect, it } from 'vitest'
import type {
  ExecutedAction,
  JsonObject,
  NodeType,
  TraversalTraceEntry,
  TreeGraphResponse,
} from '../../api/types'
import { deriveCriticalSummary } from './criticalSummary'

function entered(step: number, nodeKey: string, nodeType: NodeType, treeKey = 'clinical-tree'): TraversalTraceEntry {
  return {
    step, event: 'node_entered', tree_key: treeKey, node_key: nodeKey, node_type: nodeType,
    candidate_node_key: null, condition_definition: null, condition_result: null,
    evaluation_details: null, changed_context_paths: [],
  }
}

function action(nodeKey: string, payload: JsonObject, treeKey = 'clinical-tree'): ExecutedAction {
  return {
    tree_key: treeKey, node_key: nodeKey, node_type: 'ACTION',
    text_en: 'Change treatment and arrange follow-up', text_vi: 'Đổi điều trị và hẹn tái khám',
    payload,
  }
}

function summary(
  risk: string,
  log: TraversalTraceEntry[] = [entered(1, 'T1_START', 'START')],
  actions: ExecutedAction[] = [action('T4_ACTION_ADD_DRUG', { action_type: 'ADD_DRUG', follow_up_required: true })],
  graphs: Record<string, TreeGraphResponse> = {},
) {
  return deriveCriticalSummary({
    log, actions, graphs, locale: 'en',
    context: risk ? { risk: { level: risk } } : {},
  })
}

describe('deriveCriticalSummary follow-up policy', () => {
  it.each([
    ['HIGH', 'In 2 weeks'],
    ['VERY_HIGH', 'In 2 weeks'],
    ['MODERATE', 'In 3 weeks'],
    ['LOW', 'In 4 weeks'],
    ['', 'In 4 weeks'],
  ])('maps %s risk to %s when the tree gives no exact interval', (risk, timing) => {
    expect(summary(risk).followUp?.timing).toBe(timing)
  })

  it('keeps exact tree timing ahead of the risk policy', () => {
    const result = summary('HIGH', undefined, [
      action('T4_ACTION_ADD_DRUG', { follow_up_required: true, follow_up_days: 5 }),
    ])
    expect(result.followUp?.timing).toBe('In 5 days')
    expect(result.followUp?.source).toBe('Explicit tree instruction')
  })

  it('uses the obstetric review window for active pregnancy hypertension', () => {
    const log = [
      entered(1, 'T12_START_PREGNANCY_HTN_SEQUENCE', 'START', 'hypertension-in-pregnancy'),
      entered(2, 'T12_INF_GESTATIONAL_HTN_CLASSIFICATION', 'INFERENCE', 'hypertension-in-pregnancy'),
    ]
    expect(summary('', log, [
      action('T12_END_REFER_OBGYN', { follow_up_required: true }, 'hypertension-in-pregnancy'),
    ]).followUp?.timing).toBe('Within 1 week')
  })

  it('uses the postpartum review window', () => {
    const log = [entered(1, 'T12_C_POSTPARTUM', 'CONDITION', 'hypertension-in-pregnancy')]
    expect(summary('', log, [
      action('T12_END_MAINTAIN_REGIMEN_POSTPARTUM', { follow_up_required: true }, 'hypertension-in-pregnancy'),
    ]).followUp?.timing).toBe('Within 7–10 days')
  })

  it('overrides scheduled follow-up for an emergency branch', () => {
    const log = [
      entered(1, 'T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN', 'ACTION', 'hypertensive-emergency'),
    ]
    const result = summary('', log, [
      action('T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN', {
        action_type: 'ADMIT_AND_DETERMINE_TARGET_ORGAN', follow_up_required: false,
      }, 'hypertensive-emergency'),
    ])
    expect(result.urgency).toBe('immediate')
    expect(result.followUp?.timing).toBe('Immediate / same day')
  })
})

describe('deriveCriticalSummary important path', () => {
  it('keeps material decisions and treatments while dropping start and maintenance nodes', () => {
    const graph: TreeGraphResponse = {
      tree: { tree_key: 'clinical-tree', name_en: 'Risk and treatment', name_vi: 'Nguy cơ và điều trị' },
      start_node_key: 'T2_START',
      nodes: [
        node('T2_START', 'START', 'Start'),
        node('T2_C_HIGH_RISK', 'CONDITION', 'High cardiovascular risk'),
        node('T2_INF_HIGH_RISK', 'INFERENCE', 'Classify as high risk'),
        node('T4_ACTION_ADD_DRUG', 'ACTION', 'Add antihypertensive drug', { action_type: 'ADD_DRUG' }),
        node('T4_END_MAINTAIN_REGIMEN', 'END', 'Maintain regimen', { action_type: 'MAINTAIN_CURRENT_REGIMEN' }),
      ],
      edges: [], global_nodes: [], references: [],
    }
    const log = [
      entered(1, 'T2_START', 'START'),
      {
        ...entered(2, 'T2_START', 'START'),
        event: 'candidate_evaluated' as const,
        candidate_node_key: 'T2_C_HIGH_RISK',
        condition_result: true,
        evaluation_details: {
          kind: 'comparison', operator: 'eq', result: true,
          left: { kind: 'path', path: 'context.risk.level', value: 'HIGH' },
          right: { kind: 'literal', value: 'HIGH' },
        },
      },
      entered(3, 'T2_C_HIGH_RISK', 'CONDITION'),
      { ...entered(4, 'T2_INF_HIGH_RISK', 'INFERENCE'), changed_context_paths: ['context.risk.level'] },
      entered(5, 'T4_ACTION_ADD_DRUG', 'ACTION'),
      entered(6, 'T4_END_MAINTAIN_REGIMEN', 'END'),
    ]
    const path = summary('HIGH', log, [
      action('T4_ACTION_ADD_DRUG', { action_type: 'ADD_DRUG', follow_up_required: true }),
      action('T4_END_MAINTAIN_REGIMEN', { action_type: 'MAINTAIN_CURRENT_REGIMEN' }),
    ], { 'clinical-tree': graph }).path

    expect(path.map((step) => step.label)).toEqual([
      'High cardiovascular risk',
      'Classify as high risk',
      'Add antihypertensive drug',
    ])
    expect(path[0]?.detail).toBe('Risk level: High')
  })
})

function node(
  nodeKey: string,
  nodeType: NodeType,
  textEn: string,
  actionPayload: JsonObject | null = null,
): TreeGraphResponse['nodes'][number] {
  return {
    node_key: nodeKey, node_type: nodeType, text_en: textEn, text_vi: textEn,
    condition_definition: null, context_patch: null, action_payload: actionPayload,
    link_target_tree_key: null, link_target_node_key: null, display_order: 1,
  }
}
