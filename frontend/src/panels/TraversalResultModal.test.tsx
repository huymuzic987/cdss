// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EvaluationResponse } from '../api/types'
import { TraversalResultModal } from './TraversalResultModal'

const canonicalBundleModules = import.meta.glob('../../../data/fhir/test_case/*.json', {
  eager: true,
  import: 'default',
}) as Record<string, EvaluationResponse['input_snapshot']>
const canonicalBundles = Object.entries(canonicalBundleModules)

const result: EvaluationResponse = {
  status: 'success', input_snapshot: { patient_marker: 'Rule-specific input' }, context: {},
  actions: [{
    tree_key: 'example-rule', node_key: 'EXAMPLE_END', node_type: 'END',
    text_en: 'Use the recommended interventions and reassess.',
    text_vi: 'Áp dụng các can thiệp được khuyến nghị và đánh giá lại.',
    payload: { presentation: {
      schema_version: '1.0',
      alert: { text_en: 'The patient-specific findings meet this rule threshold.', text_vi: 'Các phát hiện đáp ứng ngưỡng.' },
      trigger_evidence: [
        { id: 'finding', label_en: 'Qualifying finding', label_vi: 'Phát hiện phù hợp', value: 'Present' },
        { id: 'result', label_en: 'Latest result', label_vi: 'Kết quả mới nhất', value: 42, unit: 'units' },
      ],
      recommendation: { text_en: 'Place the appropriate orders and arrange follow-up.', text_vi: 'Chỉ định và hẹn tái khám.' },
      recommended_orders: [
        { id: 'medication-order', type: 'medication', name_en: 'Catalog medication', name_vi: 'Thuốc danh mục', starting_dose: '5 mg', class_label_en: 'Catalog class', class_label_vi: 'Nhóm thuốc' },
        { id: 'laboratory-order', type: 'laboratory', name_en: 'Monitoring laboratory test', name_vi: 'Xét nghiệm theo dõi' },
        {
          id: 'class-combination', type: 'medication',
          name_en: 'Drug Class A + Drug Class C', name_vi: 'Nhóm thuốc A + Nhóm thuốc C',
          class_label_en: 'Drug Class A + Drug Class C', class_label_vi: 'Nhóm thuốc A + Nhóm thuốc C',
          dose_strategy: 'LOW_DOSE',
          drug_classes: [
            {
              code: 'A', label_en: 'Drug Class A', label_vi: 'Nhóm thuốc A',
              dose_label_en: 'Low dose', dose_label_vi: 'Liều thấp',
              medicines: [{ id: 'losartan', name: 'Losartan', dose: '25 mg', subgroup: 'ARB' }],
            },
            {
              code: 'C', label_en: 'Drug Class C', label_vi: 'Nhóm thuốc C',
              dose_label_en: 'Low dose', dose_label_vi: 'Liều thấp',
              medicines: [{ id: 'amlodipine', name: 'Amlodipine', dose: '2.5 mg', subgroup: 'DHP CCB' }],
            },
          ],
        },
      ],
      additional_actions: [
        { id: 'follow-up', label_en: 'Schedule follow-up', label_vi: 'Hẹn tái khám' },
        { id: 'patient-discussion', label_en: 'Discuss with patient', label_vi: 'Trao đổi với người bệnh' },
      ],
      acknowledgement_options: [
        { id: 'alternative-plan', label_en: 'Use an alternative plan', label_vi: 'Dùng phương án khác' },
        { id: 'other', label_en: 'Other', label_vi: 'Khác', requires_text: true },
      ],
      clinical_details: [], guideline_references: [],
    } },
  }],
  traversal_log: [
    { step: 1, event: 'node_entered', tree_key: 'hypertension-diagnosis', node_key: 'T1_START', node_type: 'START', candidate_node_key: null, condition_definition: null, condition_result: null, evaluation_details: null, changed_context_paths: [] },
    { step: 2, event: 'node_entered', tree_key: 'hypertension-diagnosis', node_key: 'T1_COND_PREGNANT', node_type: 'CONDITION', candidate_node_key: null, condition_definition: null, condition_result: null, evaluation_details: null, changed_context_paths: [] },
    { step: 3, event: 'node_entered', tree_key: 'example-rule', node_key: 'EXAMPLE_END', node_type: 'END', candidate_node_key: null, condition_definition: null, condition_result: null, evaluation_details: null, changed_context_paths: [] },
  ],
  references: [],
  tree_metadata: [
    { tree_key: 'hypertension-diagnosis', name_en: 'Hypertension diagnosis', name_vi: 'Chẩn đoán tăng huyết áp' },
    { tree_key: 'example-rule', name_en: 'Treatment recommendation', name_vi: 'Khuyến nghị điều trị' },
  ],
  started_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:00:01Z',
  inferred_follow_up_type: null, previous_recommended_action_types: [],
}

afterEach(cleanup)

function renderModal(modalResult = result) {
  const onClose = vi.fn()
  render(<TraversalResultModal result={modalResult} partial={null} onClose={onClose} locale="en" />)
  return { onClose }
}

describe('TraversalResultModal', () => {
  it.each(canonicalBundles)(
    'renders structured presentation with raw canonical Bundle %s',
    (_fixturePath, bundle) => {
      renderModal({ ...result, input_snapshot: bundle })

      expect(screen.getByText('Clinical decision support recommendation')).toBeTruthy()
      expect(screen.getByText('Qualifying finding')).toBeTruthy()
      expect(screen.getByText('Place the appropriate orders and arrange follow-up.')).toBeTruthy()
    },
  )

  it('removes redundant and technical recommendation UI', () => {
    renderModal()

    expect(screen.queryByText('Patient-specific alert')).toBeNull()
    expect(screen.queryByText('The patient-specific findings meet this rule threshold.')).toBeNull()
    expect(screen.queryByText('View guideline')).toBeNull()
    expect(screen.queryByText('Clinical details')).toBeNull()
    expect(screen.queryByText('Recommended order options')).toBeNull()
    expect(screen.queryByRole('radio', { name: 'Order' })).toBeNull()
    expect(screen.queryByRole('radio', { name: 'Do not order' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Acknowledge / Save decision' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Accept recommendation' })).toBeNull()
    expect(screen.getByText('Drug Class A')).toBeTruthy()
    expect(screen.getByText('Drug Class C')).toBeTruthy()
  })

  it('shows medicine names with only the action-selected low doses on class hover', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.hover(screen.getByText('Drug Class A'))

    const tooltip = screen.getByRole('tooltip')
    expect(tooltip.textContent).toContain('Drug Class A · Low dose')
    expect(tooltip.textContent).toContain('Losartan')
    expect(tooltip.textContent).toContain('25 mg')
    expect(tooltip.textContent).not.toContain('50 - 100 mg')
  })

  it('shows a clinician-readable full decision path without raw node keys', async () => {
    const user = userEvent.setup()
    renderModal()
    await user.click(screen.getByText('Full decision path'))

    expect(screen.getByText('Begin clinical assessment')).toBeTruthy()
    expect(screen.getByText('Assess: Pregnant')).toBeTruthy()
    expect(screen.getByText('Use the recommended interventions and reassess.')).toBeTruthy()
    expect(screen.queryByText('T1_COND_PREGNANT')).toBeNull()
    expect(screen.queryByText('EXAMPLE_END')).toBeNull()
  })

})
