// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
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
  traversal_log: [], references: [], tree_metadata: [],
  started_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:00:01Z',
  inferred_follow_up_type: null, previous_recommended_action_types: [],
}

afterEach(cleanup)

function renderModal(onSubmit = vi.fn(), modalResult = result) {
  const onClose = vi.fn()
  render(<TraversalResultModal result={modalResult} partial={null} onClose={onClose} onSubmit={onSubmit} locale="en" />)
  return { onClose, onSubmit }
}

function orderRow(name: string) {
  const row = screen.getAllByText(name)[0].closest('.cds-order-row')
  if (!row) throw new Error(`Order row not found for ${name}`)
  return within(row as HTMLElement)
}

describe('TraversalResultModal', () => {
  it.each(canonicalBundles)(
    'renders structured presentation with raw canonical Bundle %s',
    (_fixturePath, bundle) => {
      renderModal(vi.fn(), { ...result, input_snapshot: bundle })

      expect(screen.getByText('The patient-specific findings meet this rule threshold.')).toBeTruthy()
      expect(screen.getByText('Qualifying finding')).toBeTruthy()
      expect(screen.getByText('Place the appropriate orders and arrange follow-up.')).toBeTruthy()
    },
  )

  it('selects an order and enables the place-orders action', async () => {
    const user = userEvent.setup()
    renderModal()
    const accept = screen.getByRole('button', { name: 'Accept and place orders' })
    expect(accept).toBeDisabled()
    await user.click(orderRow('Catalog medication').getByRole('radio', { name: 'Order' }))
    expect(accept).toBeEnabled()
  })

  it('shows acknowledgement options after declining a recommendation', async () => {
    const user = userEvent.setup()
    renderModal()
    expect(screen.queryByRole('heading', { name: 'Acknowledgement reason' })).toBeNull()
    await user.click(orderRow('Catalog medication').getByRole('radio', { name: 'Do not order' }))
    expect(screen.getByRole('heading', { name: 'Acknowledgement reason' })).toBeTruthy()
  })

  it('blocks deferred submission until an acknowledgement reason is selected', async () => {
    const user = userEvent.setup()
    const { onSubmit } = renderModal()
    await user.click(screen.getByRole('button', { name: 'Acknowledge / Save decision' }))
    expect(screen.getByRole('alert').textContent).toContain('Select an acknowledgement reason')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('requires text for acknowledgement options configured to require it', async () => {
    const user = userEvent.setup()
    const { onSubmit } = renderModal()
    await user.click(screen.getByRole('button', { name: 'Acknowledge / Save decision' }))
    await user.click(screen.getByRole('radio', { name: 'Other' }))
    await user.click(screen.getByRole('button', { name: 'Acknowledge / Save decision' }))
    expect(screen.getByRole('alert').textContent).toContain('Enter the acknowledgement reason')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits selected orders and additional actions without duplicate orders', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    renderModal(onSubmit)
    await user.click(orderRow('Catalog medication').getByRole('radio', { name: 'Order' }))
    await user.click(screen.getByRole('checkbox', { name: 'Schedule follow-up' }))
    await user.click(screen.getByRole('button', { name: 'Accept and place orders' }))
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      mode: 'place-orders', additionalActions: ['follow-up'], acknowledgement: null,
      orders: expect.arrayContaining([expect.objectContaining({ id: 'medication-order', decision: 'order' })]),
    }))
    const payload = onSubmit.mock.calls[0][0]
    expect(new Set(payload.orders.map((order: { id: string }) => order.id)).size).toBe(payload.orders.length)
  })
})
