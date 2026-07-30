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
  status: 'success', input_snapshot: { patient_marker: 'Rule-specific input', risk_factor_count: 4 },
  context: { diagnosis: { hypertension_class: 'GRADE_2_HYPERTENSION' }, risk: { level: 'HIGH' } },
  actions: [{
    tree_key: 'example-rule', node_key: 'EXAMPLE_END', node_type: 'END',
    text_en: 'Use the recommended interventions and reassess.',
    text_vi: 'Áp dụng các can thiệp được khuyến nghị và đánh giá lại.',
    payload: { action_type: 'FINAL_REASSESSMENT', presentation: {
      schema_version: '1.0',
      alert: { text_en: 'The patient-specific findings meet this rule threshold.', text_vi: 'Các phát hiện đáp ứng ngưỡng.' },
      alert_summary: {
        text_en: 'Patient has High Hypertension Risk; SBP ≥ 180 mmHg OR DBP ≥ 120 mmHg',
        text_vi: 'Bệnh nhân có nguy cơ tăng huyết áp cao; HATT ≥ 180 mmHg HOẶC HATTr ≥ 120 mmHg',
        findings: [
          {
            code: 'has_target_organ_damage',
            label_en: 'Target-organ damage',
            label_vi: 'Tổn thương cơ quan đích',
            tree_key: 'hypertensive-emergency',
            node_key: 'T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE',
          },
          {
            code: 'has_tia',
            label_en: 'Transient ischemic attack',
            label_vi: 'Cơn thiếu máu não thoáng qua',
            tree_key: 'risk-classification',
            node_key: 'T2_C_HIGH_RISK_COMORBIDITY_PRESENT',
          },
          {
            code: 'has_stroke',
            label_en: 'Stroke',
            label_vi: 'Đột quỵ',
            tree_key: 'risk-classification',
            node_key: 'T2_C_HIGH_RISK_COMORBIDITY_PRESENT',
          },
          {
            code: 'has_cardiovascular_disease',
            label_en: 'Cardiovascular disease',
            label_vi: 'Bệnh tim mạch',
            tree_key: 'risk-classification',
            node_key: 'T2_C_HIGH_RISK_COMORBIDITY_PRESENT',
          },
        ],
      },
      trigger_evidence: [
        { id: 'current-sbp', label_en: 'Current systolic blood pressure', label_vi: 'Huyết áp tâm thu hiện tại', value: 150, unit: 'mmHg' },
        { id: 'current-dbp', label_en: 'Current diastolic blood pressure', label_vi: 'Huyết áp tâm trương hiện tại', value: 92, unit: 'mmHg' },
        { id: 'finding', label_en: 'Qualifying finding', label_vi: 'Phát hiện phù hợp', value: 'Present' },
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
          strategy_references: [{
            id: 'drug-combination:T6_INF_INITIATE_TWO_DRUG_LOW_DOSE:1',
            tree_key: 'drug-combination',
            tree_name_en: 'Drug combination',
            tree_name_vi: 'Phối hợp thuốc',
            node_key: 'T6_INF_INITIATE_TWO_DRUG_LOW_DOSE',
            node_text_en: 'Drug therapy: start with 2 low-dose drugs (A combined with C or D)',
            node_text_vi: 'Điều trị thuốc khởi đầu bằng 2 thuốc liều thấp',
            title_en: 'VSH/VNHA Hypertension Guideline 2022',
            title_vi: 'Khuyến cáo VSH/VNHA về tăng huyết áp 2022',
            section_path: [{ number: '3.5', title: 'Combination treatment strategy' }],
            locator: 'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
            locator_detail: 'Prefer A+C or A+D at low dose.',
            printed_page_numbers: [20],
            pdf_page_numbers: [22],
            note: 'Use a low-dose fixed combination.',
          }],
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
      clinical_details: [
        { id: 'ckd', category: 'condition', label_en: 'Condition', label_vi: 'Chẩn đoán', value: 'Chronic kidney disease' },
        { id: 'raw-cvd', category: 'condition', label_en: 'Condition', label_vi: 'Chẩn đoán', value: 'has_cardiovascular_disease' },
        { id: 'raw-stroke', category: 'condition', label_en: 'Condition', label_vi: 'Chẩn đoán', value: 'has_stroke' },
        { id: 'raw-tia', category: 'condition', label_en: 'Condition', label_vi: 'Chẩn đoán', value: 'has_tia' },
        { id: 'refuted-diabetes', category: 'condition', label_en: 'Condition', label_vi: 'Chẩn đoán', value: 'Diabetes', active: false },
      ],
      guideline_references: [],
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
      expect(screen.getByText('150/92 mmHg')).toBeTruthy()
      expect(screen.getByText('Use the recommended interventions and reassess.')).toBeTruthy()
    },
  )

  it('shows current BP and active conditions without repeating HTN risk', () => {
    renderModal()

    expect(screen.getByText('Blood Pressure')).toBeTruthy()
    expect(screen.getByText('150/92 mmHg')).toBeTruthy()
    expect(screen.queryByText('HTN risk level:')).toBeNull()
    expect(screen.queryByText('High risk')).toBeNull()
    expect(screen.getByText(
      'Patient has 5 conditions/comorbidities and 4 risk factors.',
    )).toBeTruthy()
    expect(screen.queryByText('Conditions')).toBeNull()
    expect(screen.queryByText(/Target-organ damage, Transient ischemic attack, Stroke/)).toBeNull()
    expect(screen.queryByText(/has_cardiovascular_disease|has_stroke|has_tia/)).toBeNull()
    expect(screen.queryByText('Diabetes')).toBeNull()
    expect(screen.queryByText('Hypertension stage')).toBeNull()
    expect(screen.queryByText('Diagnoses and comorbidities')).toBeNull()
    expect(screen.queryByText('Treatment indication')).toBeNull()
    expect(screen.queryByText('Qualifying finding')).toBeNull()
  })

  it('keeps detailed diseases out of the alert summary and removes blood pressure', () => {
    renderModal()

    expect(screen.getByLabelText('Alert summary').textContent).toBe(
      'Patient has High Hypertension Risk',
    )
    expect(screen.queryByText(/SBP ≥ 180/)).toBeNull()
    expect(screen.queryByText(/DBP ≥ 120/)).toBeNull()
  })

  it('keeps the standard warning style for the traversed emergency branch', () => {
    const emergencyResult = structuredClone(result)
    const presentation = emergencyResult.actions[0].payload.presentation
    if (!presentation || typeof presentation !== 'object' || Array.isArray(presentation)) {
      throw new Error('Expected structured presentation fixture')
    }
    const alertSummary = presentation.alert_summary
    if (!alertSummary || typeof alertSummary !== 'object' || Array.isArray(alertSummary)) {
      throw new Error('Expected structured alert summary fixture')
    }
    alertSummary.text_en = 'Patient has Emergency Hypertension'
    alertSummary.hypertensive_crisis_classification = {
      code: 'EMERGENCY_HYPERTENSION',
      label_en: 'Emergency Hypertension',
      label_vi: 'Tăng huyết áp cấp cứu',
    }

    renderModal(emergencyResult)

    const summary = screen.getByLabelText('Alert summary')
    expect(summary.className).toBe('cds-alert-summary')
    expect(screen.queryByText('Critical')).toBeNull()
    expect(screen.getByText('Patient has Emergency Hypertension')).toBeTruthy()
  })

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
    expect(screen.queryByText('Additional clinical actions')).toBeNull()
    expect(screen.queryByText('Schedule follow-up')).toBeNull()
    expect(screen.queryByText('Discuss with patient')).toBeNull()
    expect(screen.getByText('Drug Class A')).toBeTruthy()
    expect(screen.getByText('Drug Class C')).toBeTruthy()
  })

  it('uses the final action or end node text for Recommended Action', () => {
    renderModal({
      ...result,
      actions: [
        {
          tree_key: 'example-rule',
          node_key: 'EXAMPLE_INTERMEDIATE_ACTION',
          node_type: 'ACTION',
          text_en: 'Intermediate technical action.',
          text_vi: 'Hành động kỹ thuật trung gian.',
          payload: { action_type: 'INTERMEDIATE_CHECK' },
        },
        ...result.actions,
      ],
    })

    expect(screen.getByText('Use the recommended interventions and reassess.')).toBeTruthy()
    expect(screen.queryByText('Intermediate technical action.')).toBeNull()
    expect(screen.queryByText('FINAL_REASSESSMENT')).toBeNull()
  })

  it('shows Recommended Action only in English for the Vietnamese locale', () => {
    render(
      <TraversalResultModal
        result={result}
        partial={null}
        onClose={vi.fn()}
        locale="vi"
      />,
    )

    expect(screen.getByText('Use the recommended interventions and reassess.')).toBeTruthy()
    expect(screen.queryByText('Áp dụng các can thiệp được khuyến nghị và đánh giá lại.')).toBeNull()
  })

  it('shows medicine names with only the action-selected low doses after a class click', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.hover(screen.getByText('Drug Class A'))
    expect(screen.queryByRole('tooltip')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Drug Class A' }))

    const tooltip = screen.getByRole('tooltip')
    expect(tooltip.textContent).toContain('Drug Class A · Low dose')
    expect(tooltip.textContent).toContain('Losartan')
    expect(tooltip.textContent).toContain('25 mg')
    expect(tooltip.textContent).toContain('Guideline source')
    expect(tooltip.textContent).toContain('VSH/VNHA Hypertension Guideline 2022')
    expect(tooltip.textContent).toContain('Section')
    expect(tooltip.textContent).toContain('Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc')
    expect(tooltip.textContent).not.toContain('50 - 100 mg')

    await user.click(screen.getByRole('button', { name: 'Drug Class A' }))
    expect(screen.queryByRole('tooltip')).toBeNull()
  })

  it('keeps drug-class reference details inside the medicine popover', async () => {
    const user = userEvent.setup()
    renderModal()

    expect(screen.queryByRole('button', { name: 'Bảng 9' })).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Drug Class A' }))

    const tooltip = screen.getByRole('tooltip')
    expect(tooltip.textContent).toContain('Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc')
    expect(tooltip.textContent).toContain('VSH/VNHA Hypertension Guideline 2022')
    expect(screen.getAllByText('Guideline source')).toHaveLength(1)
    expect(screen.getAllByText('Section')).toHaveLength(1)
    expect(tooltip.textContent).not.toContain('Drug therapy: start with 2 low-dose drugs')
    expect(tooltip.textContent).not.toContain('Decision tree: Drug combination')
    expect(tooltip.textContent).not.toContain('Prefer A+C or A+D at low dose.')
    expect(tooltip.textContent).not.toContain('Use a low-dose fixed combination.')
  })

  it('shows every entered node in the full decision path', async () => {
    const user = userEvent.setup()
    renderModal({
      ...result,
      traversal_log: [
        ...result.traversal_log.slice(0, 2),
        {
          step: 3, event: 'node_entered', tree_key: 'drug-combination',
          node_key: 'T6_INF_DETERMINE_PRIOR_PRESCRIPTION_STATUS', node_type: 'INFERENCE',
          candidate_node_key: null, condition_definition: null, condition_result: null,
          evaluation_details: null, changed_context_paths: ['context.treatment.has_prior_prescription'],
        },
        {
          step: 4, event: 'node_entered', tree_key: 'drug-combination',
          node_key: 'T6_INF_INITIATE_TWO_DRUG_LOW_DOSE', node_type: 'INFERENCE',
          candidate_node_key: null, condition_definition: null, condition_result: null,
          evaluation_details: null,
          changed_context_paths: ['context.treatment_preferences.combination_options'],
        },
        { ...result.traversal_log[2], step: 5 },
      ],
    })
    await user.click(screen.getByText('Full decision path'))

    expect(screen.getByText('Begin clinical assessment')).toBeTruthy()
    expect(screen.getByText('Assess: Pregnant')).toBeTruthy()
    expect(screen.getByText('Determine: Determine prior prescription status')).toBeTruthy()
    expect(screen.getByText('Determine: Initiate two drug low dose')).toBeTruthy()
    expect(screen.getByText('Use the recommended interventions and reassess.')).toBeTruthy()
    expect(screen.queryByText('T1_COND_PREGNANT')).toBeNull()
    expect(screen.queryByText('EXAMPLE_END')).toBeNull()
  })

})
