// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ApiErrorResponse, EvaluationResponse, TreeGraphResponse } from '../api/types'
import { TraversalResultModal } from './TraversalResultModal'

const presentation = {
  schema_version: '1.0',
  alert: { text_en: 'Clinical decision support recommendation', text_vi: 'Khuyến nghị hỗ trợ quyết định.' },
  trigger_evidence: [
    { id: 'noise', label_en: 'Generic evidence', label_vi: 'Dữ kiện chung', value: 'Present' },
  ],
  recommendation: { text_en: 'Start treatment and arrange follow-up.', text_vi: 'Bắt đầu điều trị và hẹn tái khám.' },
  recommended_orders: [{
    id: 'combination', type: 'medication',
    name_en: 'Drug Class A + Drug Class C', name_vi: 'Nhóm thuốc A + Nhóm thuốc C',
    class_label_en: 'Drug Class A + Drug Class C', class_label_vi: 'Nhóm thuốc A + Nhóm thuốc C',
    dose_strategy: 'LOW_DOSE',
    drug_classes: [{
      code: 'A', label_en: 'Drug Class A', label_vi: 'Nhóm thuốc A',
      dose_label_en: 'Low dose', dose_label_vi: 'Liều thấp',
      medicines: [{ id: 'losartan', name: 'Losartan', dose: '25 mg', subgroup: 'ARB' }],
    }, {
      code: 'C', label_en: 'Drug Class C', label_vi: 'Nhóm thuốc C',
      dose_label_en: 'Low dose', dose_label_vi: 'Liều thấp',
      medicines: [{ id: 'amlodipine', name: 'Amlodipine', dose: '2.5 mg', subgroup: 'DHP CCB' }],
    }],
  }],
  additional_actions: [{ id: 'follow-up', label_en: 'Schedule follow-up', label_vi: 'Hẹn tái khám' }],
  acknowledgement_options: [],
  clinical_details: [],
  guideline_references: [],
}

const result: EvaluationResponse = {
  status: 'success',
  input_snapshot: { patient_marker: 'Rule-specific input' },
  context: { risk: { level: 'HIGH' } },
  actions: [{
    tree_key: 'treatment-tree', node_key: 'T4_ACTION_ADD_DRUG', node_type: 'ACTION',
    text_en: 'Add combination therapy', text_vi: 'Thêm phối hợp thuốc',
    payload: { action_type: 'ADD_DRUG', follow_up_required: true, presentation },
  }],
  traversal_log: [
    trace(1, 'node_entered', 'T1_START', 'START'),
    {
      ...trace(2, 'candidate_evaluated', 'T1_START', 'START'),
      candidate_node_key: 'T1_COND_PREGNANT',
      condition_definition: { op: 'eq', path: 'input.is_pregnant', value: true },
      condition_result: true,
      evaluation_details: {
        kind: 'comparison', operator: 'eq', result: true,
        left: { kind: 'path', path: 'input.is_pregnant', value: true },
        right: { kind: 'literal', value: true },
      },
    },
    trace(3, 'node_entered', 'T1_COND_PREGNANT', 'CONDITION'),
    trace(4, 'node_entered', 'T4_ACTION_ADD_DRUG', 'ACTION', 'treatment-tree'),
  ],
  references: [{
    tree_key: 'treatment-tree', node_key: 'T4_ACTION_ADD_DRUG', reference_order: 1,
    source_title: 'Example hypertension guideline',
    section_path: [{ title: 'Treatment', number: '4.2' }],
    locator: 'Table 4', locator_detail: 'Drug selection',
    reference_note: 'Use the selected classes for this phenotype.',
  }],
  tree_metadata: [
    { tree_key: 'hypertension-diagnosis', name_en: 'Hypertension diagnosis', name_vi: 'Chẩn đoán tăng huyết áp' },
    { tree_key: 'treatment-tree', name_en: 'Treatment', name_vi: 'Điều trị' },
  ],
  started_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:00:01Z',
  inferred_follow_up_type: null, previous_recommended_action_types: [], pregnancy_follow_up: null,
}

function trace(
  step: number,
  event: EvaluationResponse['traversal_log'][number]['event'],
  nodeKey: string,
  nodeType: EvaluationResponse['traversal_log'][number]['node_type'],
  treeKey = 'hypertension-diagnosis',
): EvaluationResponse['traversal_log'][number] {
  return {
    step, event, tree_key: treeKey, node_key: nodeKey, node_type: nodeType,
    candidate_node_key: null, condition_definition: null, condition_result: null,
    evaluation_details: null, changed_context_paths: [],
  }
}

function renderModal(
  modalResult = result,
  graphs: Record<string, TreeGraphResponse> = {},
) {
  render(
    <TraversalResultModal
      result={modalResult}
      partial={null}
      graphs={graphs}
      onClose={vi.fn()}
      locale="en"
    />,
  )
}

afterEach(cleanup)

describe('TraversalResultModal', () => {
  it('shows the collection path and final B regimen without legacy orders', () => {
    const regimenPresentation = {
      ...presentation,
      regimen_plan: {
        schema_version: '1.0',
        steps: [{
          id: 'add-b',
          keyword: 'ADD',
          text_en: 'Add beta-blocker',
          text_vi: 'ThÃªm thuá»‘c cháº¹n Beta',
          components: [{ selector_kind: 'class', code: 'B', dose_strategy: 'LOW_DOSE' }],
          alternatives: [],
        }],
        effective_regimen: {
          base_options: [],
          additions: [{ selector_kind: 'class', code: 'B', dose_strategy: 'LOW_DOSE' }],
          stopped_components: [],
          constraints: [],
        },
      },
    }
    const action = {
      ...result.actions[0]!,
      payload: { ...result.actions[0]!.payload, presentation: regimenPresentation },
    }

    renderModal({ ...result, actions: [action] })

    expect(screen.getByText('Drug collection path')).toBeTruthy()
    expect(screen.getByText('ADD')).toBeTruthy()
    expect(screen.getByText('Final drug regimen')).toBeTruthy()
    expect(screen.getByText('Option 1')).toBeTruthy()
    expect(screen.getAllByText('B')).toHaveLength(2)
    expect(screen.getAllByText('Low dose')).toHaveLength(2)
    expect(screen.getAllByText('Use all components together').length).toBeGreaterThan(0)
    expect(document.querySelector('.cds-order-row')).toBeNull()
    expect(screen.queryByText('Amlodipine')).toBeNull()
  })

  it('renders alternative bases as complete OR regimens with additions in both', () => {
    const regimenPresentation = {
      ...presentation,
      regimen_plan: {
        schema_version: '1.0',
        steps: [],
        effective_regimen: {
          base_options: [
            { components: [{ code: 'A' }, { code: 'C' }] },
            { components: [{ code: 'A' }, { code: 'D' }] },
          ],
          additions: [{ code: 'B' }],
          stopped_components: [],
          constraints: [],
        },
      },
    }
    const action = {
      ...result.actions[0]!,
      payload: { ...result.actions[0]!.payload, presentation: regimenPresentation },
    }

    renderModal({ ...result, actions: [action] })

    const options = document.querySelectorAll('.cds-final-regimen')
    const optionLabels = [...options].map((option) => (
      [...option.querySelectorAll('.cds-regimen-component > strong')].map((item) => item.textContent)
    ))
    expect(options).toHaveLength(2)
    expect(optionLabels[0]).toEqual(['A', 'C', 'B'])
    expect(optionLabels[1]).toEqual(['A', 'D', 'B'])
    expect(screen.getByText('OR')).toBeTruthy()
    expect(screen.getByText('Choose one complete regimen')).toBeTruthy()
  })

  it('renders alert, reason, action, drugs, and path as five ordered rows', () => {
    renderModal()
    const body = screen.getByRole('dialog').querySelector('.cds-modal-body')
    const rows = Array.from(body?.children ?? []) as HTMLElement[]

    expect(rows).toHaveLength(5)
    expect(rows[0]?.classList.contains('cds-alert-high')).toBe(true)
    expect(within(rows[1]!).getByText('Matched patient findings')).toBeTruthy()
    expect(within(rows[2]!).getByText('Clinical plan')).toBeTruthy()
    expect(within(rows[3]!).getByText('Medication and orders')).toBeTruthy()
    expect(within(rows[4]!).getByText('Important decision path')).toBeTruthy()
    expect(rows.slice(0, 4).every((row) => row.hasAttribute('open'))).toBe(true)
    expect(rows[4]?.hasAttribute('open')).toBe(false)
    expect(document.querySelectorAll('.cds-section-chevron svg')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull()
  })

  it('shows the medication follow-up stop explanation in the clinical plan', () => {
    const message = 'Replace the intolerable drug within the same regimen stage and reassess'
    const followUpAction = {
      ...result.actions[0]!,
      node_key: 'T4_C_INITIAL_REGIMEN_MEDICATION_FOLLOW_UP_STOP',
      text_en: message,
      text_vi: 'Đổi thuốc không dung nạp trong cùng bậc điều trị và hẹn đánh giá lại',
      payload: {
        action_type: 'REPLACE_DRUG_SAME_STAGE',
        outcome: 'REPLACE_DRUG_SAME_STAGE',
        presentation: {
          ...presentation,
          recommendation: { text_en: message, text_vi: 'Đổi thuốc và đánh giá lại' },
          recommended_orders: [],
          additional_actions: [],
        },
      },
    }
    renderModal({
      ...result,
      context: {
        medication_follow_up: {
          outcome: 'REPLACE_DRUG_SAME_STAGE',
          should_continue_traversal: false,
          regimen_effective_date: '2026-01-29',
          next_follow_up_date: '2026-02-26',
          current_regimen_drug_classes: ['A', 'D'],
        },
      },
      actions: [followUpAction],
    })

    const plan = screen.getByText('Clinical plan').closest('details') as HTMLElement
    expect(within(plan).getByText(message)).toBeTruthy()
    expect(within(plan).getByText('Reassessment date')).toBeTruthy()
    expect(within(plan).getByText('26 Feb 2026')).toBeTruthy()
    expect(within(plan).queryByText(/weeks after the regimen effective date/)).toBeNull()
    const medication = screen.getByText('Medication and orders').closest('details') as HTMLElement
    expect(within(medication).getByText('Current regimen')).toBeTruthy()
    expect(within(medication).queryByText('Current treatment')).toBeNull()
    expect(within(medication).getByText('A')).toBeTruthy()
    expect(within(medication).getByText('D')).toBeTruthy()
  })

  it('shows controlled follow-up advice in the clinical plan but not the colored alert header', () => {
    const message = 'Blood pressure target met. Continue monitoring and maintain the current regimen.'
    renderModal({
      ...result,
      context: {
        medication_follow_up: {
          outcome: 'MAINTAIN_CONTROLLED',
          should_continue_traversal: true,
        },
      },
    })

    const plan = screen.getByText('Clinical plan').closest('details') as HTMLElement
    const alert = document.querySelector('.cds-alert-row') as HTMLElement
    expect(within(plan).getByText(message)).toBeTruthy()
    expect(within(plan).queryByText('Reassessment date')).toBeNull()
    expect(within(alert).queryByText(message)).toBeNull()
    expect(document.querySelector('.cds-alert-action')).toBeNull()
  })

  it('does not duplicate a single-class current regimen in the middle order column', () => {
    renderModal({
      ...result,
      context: {
        medication_follow_up: {
          outcome: 'REPLACE_DRUG_SAME_STAGE',
          should_continue_traversal: false,
          current_regimen_drug_classes: ['A'],
        },
      },
      actions: [],
    })

    const medication = screen.getByText('Medication and orders').closest('details') as HTMLElement
    const currentRegimen = within(medication).getByText('Current regimen')
      .closest('.cds-order-row') as HTMLElement
    expect(currentRegimen.querySelector('.cds-order-detail')?.textContent).toBe('')
    expect(within(currentRegimen).getAllByText('A')).toHaveLength(1)
  })

  it('uses urgency color and includes only route-changing patient data', () => {
    renderModal()
    const reasonSection = screen.getByText('Matched patient findings').closest('details') as HTMLElement

    expect(screen.getByRole('dialog').querySelector('.cds-alert-high')).toBeTruthy()
    expect(document.querySelector('.cds-row-heading strong')?.textContent).toBe('Hypertension')
    expect(within(reasonSection).getByText('Pregnant')).toBeTruthy()
    expect(within(reasonSection).getByText('Is pregnant')).toBeTruthy()
    expect(screen.queryByText('Clinical decision support recommendation')).toBeNull()
    expect(screen.queryByText('Generic evidence')).toBeNull()
  })

  it('uses significant disease instead of hypertension class as the alert title', () => {
    renderModal({
      ...result,
      input_snapshot: { has_type_2_diabetes: true, has_ckd: true },
      context: {
        diagnosis: { hypertension_class: 'HIGH_NORMAL_BP' },
        risk: { level: 'HIGH' },
      },
    })

    const heading = document.querySelector('.cds-row-heading strong')
    expect(heading?.textContent).toBe('Type 2 diabetes · Chronic kidney disease')
    expect(heading?.textContent).not.toContain('Hypertension class')
  })

  it('derives the disease title from the Tree 3 link route', () => {
    const treeKey = 'treatment-threshold-and-bp-target'
    const nodeKey = 'T3_LINK_18_69_TYPE_2_DIABETES_MODIFIER'
    const graph: TreeGraphResponse = {
      tree: { tree_key: treeKey, name_en: 'Treatment Threshold', name_vi: 'Treatment Threshold' },
      start_node_key: 'T3_START',
      nodes: [{
        node_key: nodeKey, node_type: 'LINK',
        text_en: 'Hypertension and Type 2 Diabetes Tree',
        text_vi: 'Hypertension and Type 2 Diabetes Tree',
        condition_definition: null, context_patch: null, action_payload: null,
        link_target_tree_key: 'hypertension-type-2-diabetes',
        link_target_node_key: null, display_order: 1,
      }],
      edges: [], global_nodes: [], references: [],
    }
    renderModal({
      ...result,
      input_snapshot: {},
      traversal_log: [
        ...result.traversal_log,
        trace(5, 'node_entered', nodeKey, 'LINK', treeKey),
      ],
    }, { [treeKey]: graph })

    expect(document.querySelector('.cds-row-heading strong')?.textContent).toBe('Type 2 diabetes')
  })

  it('prioritizes specific target-organ damage for hypertensive emergency', () => {
    renderModal({
      ...result,
      input_snapshot: {
        has_target_organ_damage: true,
        has_acute_ischemic_stroke: true,
        has_type_2_diabetes: true,
      },
    })

    expect(document.querySelector('.cds-row-heading strong')?.textContent).toBe('Acute ischemic stroke')
  })

  it.each([
    ['T12_INF_ECLAMPSIA_CLASSIFICATION', 'Eclampsia'],
    ['T12_INF_HELLP_SYNDROME', 'HELLP syndrome'],
  ])('uses the exact obstetric classification for %s', (nodeKey, expectedTitle) => {
    const treeKey = 'hypertension-in-pregnancy'
    const graph: TreeGraphResponse = {
      tree: { tree_key: treeKey, name_en: 'Pregnancy', name_vi: 'Pregnancy' },
      start_node_key: 'T12_START',
      nodes: [{
        node_key: nodeKey, node_type: 'INFERENCE',
        text_en: expectedTitle, text_vi: expectedTitle,
        condition_definition: null, context_patch: null, action_payload: null,
        link_target_tree_key: null, link_target_node_key: null, display_order: 1,
      }],
      edges: [], global_nodes: [], references: [],
    }
    renderModal({
      ...result,
      input_snapshot: {},
      traversal_log: [
        ...result.traversal_log,
        {
          ...trace(5, 'node_entered', nodeKey, 'INFERENCE', treeKey),
          changed_context_paths: ['context.pregnancy.classification'],
        },
      ],
    }, { [treeKey]: graph })

    expect(document.querySelector('.cds-row-heading strong')?.textContent).toBe(expectedTitle)
  })

  it('shows confirmed classifications as alert tags instead of finding rows', () => {
    const treeKey = 'risk-classification'
    const graph: TreeGraphResponse = {
      tree: { tree_key: treeKey, name_en: 'Risk Classification', name_vi: 'Risk Classification' },
      start_node_key: 'T2_START',
      nodes: [{
        node_key: 'T2_INF_MEDIUM_RISK', node_type: 'INFERENCE',
        text_en: 'Medium risk', text_vi: 'Medium risk',
        condition_definition: null, context_patch: null, action_payload: null,
        link_target_tree_key: null, link_target_node_key: null, display_order: 1,
      }, {
        node_key: 'T2_INF_GRADE_1_CLINIC_BP', node_type: 'INFERENCE',
        text_en: 'Grade 1 hypertension', text_vi: 'Grade 1 hypertension',
        condition_definition: null, context_patch: null, action_payload: null,
        link_target_tree_key: null, link_target_node_key: null, display_order: 2,
      }],
      edges: [], global_nodes: [], references: [],
    }
    const classification = {
      ...trace(5, 'node_entered' as const, 'T2_INF_MEDIUM_RISK', 'INFERENCE', treeKey),
      changed_context_paths: ['context.risk.level'],
    }
    const hypertensionClassification = {
      ...trace(6, 'node_entered' as const, 'T2_INF_GRADE_1_CLINIC_BP', 'INFERENCE', treeKey),
      changed_context_paths: ['context.diagnosis.hypertension_class'],
    }
    render(
      <TraversalResultModal
        result={{
          ...result,
          traversal_log: [...result.traversal_log, classification, hypertensionClassification],
        }}
        partial={null}
        graphs={{ [treeKey]: graph }}
        onClose={vi.fn()}
        locale="en"
      />,
    )

    const alert = screen.getByText('Alert').closest('details') as HTMLElement
    const findings = screen.getByText('Matched patient findings').closest('details') as HTMLElement
    const tag = within(alert).getByText('Medium risk')
    expect(tag.classList.contains('cds-confirmed-tag')).toBe(true)
    expect(tag.closest('.cds-row-heading')).toBeTruthy()
    expect(within(alert).queryByText('Grade 1 hypertension')).toBeNull()
    expect(within(findings).queryByText('Medium risk')).toBeNull()
    expect(screen.queryByText('Confirmed during clinical assessment')).toBeNull()
  })

  it('presents recommendations and review timing without acknowledgement controls', () => {
    renderModal()

    expect(screen.getByText('Start treatment and arrange follow-up.')).toBeTruthy()
    expect(screen.getAllByText('Schedule follow-up')).toHaveLength(1)
    expect(screen.getByText('In 2 weeks')).toBeTruthy()
    expect(screen.queryByRole('radio')).toBeNull()
    expect(screen.queryByText('Acknowledge / Save decision')).toBeNull()
  })

  it('keeps medication regimen text out of the clinical action section', () => {
    const medicationRecommendation = {
      ...result.actions[0]!,
      payload: {
        ...result.actions[0]!.payload,
        presentation: {
          ...presentation,
          recommendation: { text_en: 'Start Drug Class A + Drug Class C', text_vi: 'Bắt đầu phối hợp A + C' },
        },
      },
    }
    renderModal({ ...result, actions: [medicationRecommendation] })
    const plan = screen.getByText('Clinical plan').closest('details') as HTMLElement

    expect(within(plan).queryByText('Start Drug Class A + Drug Class C')).toBeNull()
    expect(within(plan).getByText('Schedule follow-up')).toBeTruthy()
    expect(within(plan).getByText('In 2 weeks')).toBeTruthy()
  })

  it('renders A/C once with dose in the middle and reveals references only from the cyan pills', async () => {
    renderModal()
    const orderRow = document.querySelector('.cds-order-row') as HTMLElement
    const hoverTarget = document.querySelector('.cds-class-hover-target') as HTMLElement

    expect(within(orderRow).getByText('Combination therapy')).toBeTruthy()
    expect(within(orderRow).getByText('Low dose')).toBeTruthy()
    expect(within(orderRow).getByText('A')).toBeTruthy()
    expect(within(orderRow).getByText('C')).toBeTruthy()
    expect(within(orderRow).queryByText(/Source node/)).toBeNull()
    expect(within(orderRow).queryByText('+ Drug Class C')).toBeNull()
    expect(within(orderRow).queryByText('Drug Class A + Drug Class C')).toBeNull()
    await userEvent.setup().hover(orderRow)
    expect(screen.queryByRole('tooltip')).toBeNull()
    hoverTarget.focus()

    const tooltip = await screen.findByRole('tooltip')
    expect(tooltip.textContent).toContain('A · RAS inhibitors')
    expect(tooltip.textContent).toContain('Low dose')
    expect(tooltip.textContent).toContain('Losartan')
    expect(tooltip.textContent).toContain('25 mg')
    expect(tooltip.textContent).not.toContain('Amlodipine')
    expect(tooltip.textContent).not.toContain('C · Calcium channel blockers')
    expect(tooltip.textContent).toContain('Add combination therapy')
    expect(tooltip.textContent).toContain('T4_ACTION_ADD_DRUG')
    expect(tooltip.textContent).toContain('Example hypertension guideline')
    expect(tooltip.textContent).toContain('Table 4')
  })

  it('explains single-drug alternatives and shows their drug group on focus', async () => {
    const alternatives = [{
      id: 'furosemide', type: 'medication',
      name_en: 'Furosemide', name_vi: 'Furosemide',
      class_label_en: 'D', class_label_vi: 'D',
      dose: '20 mg',
    }, {
      id: 'enalapril', type: 'medication',
      name_en: 'Enalapril', name_vi: 'Enalapril',
      class_label_en: 'ACE inhibitor', class_label_vi: 'Ức chế men chuyển',
      dose: '5 mg',
    }]
    const actionWithAlternatives = {
      ...result.actions[0]!,
      payload: {
        ...result.actions[0]!.payload,
        presentation: { ...presentation, recommended_orders: alternatives },
      },
    }
    renderModal({ ...result, actions: [actionWithAlternatives] })

    expect(screen.getByText('Choose one of these alternatives')).toBeTruthy()
    expect(screen.queryByText('OR')).toBeNull()
    const firstDrug = screen.getByText('Furosemide').closest('.cds-order-row') as HTMLElement
    firstDrug.focus()
    const tooltip = await screen.findByRole('tooltip')
    expect(tooltip.textContent).toContain('Drug group: D · Diuretics')
    expect(tooltip.textContent).toContain('Furosemide')
    expect(tooltip.textContent).toContain('20 mg')
  })

  it('keeps the material path collapsed by default and omits technical start nodes', async () => {
    renderModal()
    const details = screen.getByText('Important decision path').closest('details')

    expect(details?.hasAttribute('open')).toBe(false)
    await userEvent.setup().click(details!.querySelector('summary')!)
    expect(details?.hasAttribute('open')).toBe(true)
    expect(within(details!).getByText('Pregnant')).toBeTruthy()
    expect(screen.queryByText('Begin clinical assessment')).toBeNull()
    expect(screen.queryByText('T1_START')).toBeNull()
  })

  it('shows compact pregnancy episode progress inside the alert row', () => {
    renderModal({
      ...result,
      inferred_follow_up_type: 'PREGNANCY_FOLLOW_UP',
      pregnancy_follow_up: {
        episode_id: 'pregnancy-demo-001', encounter_count: 4, follow_up_number: 3,
        phase: 'FOLLOW_UP_3', minimum_follow_ups_required: 3,
        minimum_follow_ups_completed: true, next_follow_up_number: 4, next_follow_up_required: true,
        previous_visit_date: '2026-07-01T09:00:00Z',
      },
    })

    expect(screen.getByText('Pregnancy episode')).toBeTruthy()
    expect(screen.getByText(/Previous visit:/)).toBeTruthy()
    expect(screen.queryByText(/pregnancy-demo-001/)).toBeNull()
    expect(screen.queryByText(/Next requested visit/)).toBeNull()
  })

  it('uses the same compact layout for partial traversal output', () => {
    const partial: ApiErrorResponse = {
      code: 'no_matching_transition', message: 'Traversal stopped after the last valid action.',
      tree_key: 'treatment-tree', node_key: 'T4_ACTION_ADD_DRUG',
      partial_run_state: {
        input_snapshot: result.input_snapshot, context: result.context,
        actions: result.actions, traversal_log: result.traversal_log, references: result.references,
      },
    }
    render(<TraversalResultModal result={null} partial={partial} onClose={vi.fn()} locale="en" />)

    expect(screen.getByText('Traversal stopped after the last valid action.')).toBeTruthy()
    expect(screen.getByText('In 2 weeks')).toBeTruthy()
    expect(screen.getByText('Important decision path')).toBeTruthy()
  })
})
