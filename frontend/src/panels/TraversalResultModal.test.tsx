// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ApiErrorResponse, EvaluationResponse } from '../api/types'
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

function renderModal(modalResult = result) {
  render(<TraversalResultModal result={modalResult} partial={null} onClose={vi.fn()} locale="en" />)
}

afterEach(cleanup)

describe('TraversalResultModal', () => {
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
    expect(screen.getAllByText('⌄')).toHaveLength(5)
  })

  it('uses urgency color and includes only route-changing patient data', () => {
    renderModal()
    const reasonSection = screen.getByText('Matched patient findings').closest('details') as HTMLElement

    expect(screen.getByRole('dialog').querySelector('.cds-alert-high')).toBeTruthy()
    expect(within(reasonSection).getByText('Pregnant')).toBeTruthy()
    expect(within(reasonSection).getByText('Is pregnant')).toBeTruthy()
    expect(screen.queryByText('Clinical decision support recommendation')).toBeNull()
    expect(screen.queryByText('Generic evidence')).toBeNull()
  })

  it('presents recommendations and review timing without acknowledgement controls', () => {
    renderModal()

    expect(screen.getByText('Start treatment and arrange follow-up.')).toBeTruthy()
    expect(screen.getAllByText('Schedule follow-up')).toHaveLength(2)
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
    expect(within(orderRow).getByText('Drug Class A')).toBeTruthy()
    expect(within(orderRow).getByText('Drug Class C')).toBeTruthy()
    expect(within(orderRow).queryByText('+ Drug Class C')).toBeNull()
    expect(within(orderRow).queryByText('Drug Class A + Drug Class C')).toBeNull()
    await userEvent.setup().hover(orderRow)
    expect(screen.queryByRole('tooltip')).toBeNull()
    hoverTarget.focus()

    const tooltip = await screen.findByRole('tooltip')
    expect(tooltip.textContent).toContain('Drug Class A')
    expect(tooltip.textContent).toContain('Low dose')
    expect(tooltip.textContent).toContain('Losartan')
    expect(tooltip.textContent).toContain('25 mg')
    expect(tooltip.textContent).toContain('Add combination therapy')
    expect(tooltip.textContent).toContain('T4_ACTION_ADD_DRUG')
    expect(tooltip.textContent).toContain('Example hypertension guideline')
    expect(tooltip.textContent).toContain('Table 4')
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
