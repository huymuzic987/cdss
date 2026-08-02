// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { EvaluationResponse } from '../api/types'
import { PATIENT_PRESETS } from '../panels/patientPresets'
import { SHOWCASE_PATIENTS } from './showcasePatients'
import { ShowcasePage } from './ShowcasePage'

const apiMocks = vi.hoisted(() => ({ evaluateTree: vi.fn(), evaluateFollowUp: vi.fn() }))

vi.mock('../api/client', () => apiMocks)
vi.mock('../panels/TraversalResultModal', () => ({
  TraversalResultModal: ({ result, onClose }: { result: EvaluationResponse | null; onClose: () => void }) => (
    <div role="dialog"><span>{String(result?.input_snapshot.marker ?? 'partial')}</span>
      <button type="button" onClick={onClose}>Close recommendation</button></div>
  ),
}))

function evaluation(marker: string) {
  return { result: { input_snapshot: { marker } } as unknown as EvaluationResponse, partial: null, error: null }
}

function profile(presetId: string) {
  const found = SHOWCASE_PATIENTS.find((patient) => patient.presetId === presetId)
  if (!found) throw new Error(`Missing showcase preset ${presetId}`)
  return found
}

async function selectPreset(user: ReturnType<typeof userEvent.setup>, presetId: string) {
  const button = document.querySelector<HTMLButtonElement>(`[data-patient-id="${presetId}"]`)
  if (!button) throw new Error(`Missing preset button ${presetId}`)
  await user.click(button)
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolver) => { resolve = resolver })
  return { promise, resolve }
}

beforeEach(() => { apiMocks.evaluateTree.mockReset(); apiMocks.evaluateFollowUp.mockReset() })
afterEach(cleanup)

describe('ShowcasePage', () => {
  it('mirrors the mock patient preset catalog and starts without an open chart', () => {
    render(<ShowcasePage />)

    expect(SHOWCASE_PATIENTS.map(({ presetId }) => presetId)).toEqual(PATIENT_PRESETS.map(({ id }) => id))
    expect(screen.getByText(`${PATIENT_PRESETS.length} presets`)).toBeTruthy()
    expect(screen.getByText(PATIENT_PRESETS[0]!.label)).toBeTruthy()
    expect(screen.getByText('Select a preset patient to open their chart')).toBeTruthy()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('opens a diagnosis preset and evaluates its original bundle', async () => {
    apiMocks.evaluateTree.mockResolvedValue(evaluation('stage1-result'))
    const user = userEvent.setup(); render(<ShowcasePage />)
    await selectPreset(user, 'stage1-htn')

    const patient = profile('stage1-htn')
    const chart = screen.getByRole('main', { name: `${patient.name} chart` })
    expect(within(chart).getByText('Initial assessment')).toBeTruthy()
    expect(apiMocks.evaluateTree).toHaveBeenCalledWith(patient.bundle)
    expect(await screen.findByRole('dialog')).toHaveTextContent('stage1-result')
  })

  it('uses the follow-up endpoint for a known medication-stage preset', async () => {
    apiMocks.evaluateFollowUp.mockResolvedValue(evaluation('follow-up-result'))
    const user = userEvent.setup(); render(<ShowcasePage />)
    await selectPreset(user, 'med-followup-reached-full')

    const patient = profile('med-followup-reached-full')
    const chart = screen.getByRole('main', { name: `${patient.name} chart` })
    expect(within(chart).getByText('Medication follow-up')).toBeTruthy()
    expect(within(chart).getByText('Active target')).toBeTruthy()
    expect(apiMocks.evaluateFollowUp).toHaveBeenCalledWith(patient.bundle)
    expect(apiMocks.evaluateTree).not.toHaveBeenCalled()
  })

  it('shows the prior target for a lifestyle follow-up preset', async () => {
    apiMocks.evaluateTree.mockResolvedValue(evaluation('lifestyle-result'))
    const user = userEvent.setup(); render(<ShowcasePage />)
    await selectPreset(user, 'lifestyle-followup')

    const chart = screen.getByRole('main', { name: `${profile('lifestyle-followup').name} chart` })
    expect(within(chart).getByText('Lifestyle follow-up')).toBeTruthy()
    expect(within(chart).getByText('Previous target')).toBeTruthy()
  })

  it('does not surface a stale result after selecting another preset', async () => {
    const first = deferred<ReturnType<typeof evaluation>>(), second = deferred<ReturnType<typeof evaluation>>()
    apiMocks.evaluateTree.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const user = userEvent.setup(); render(<ShowcasePage />)
    await selectPreset(user, 'stage1-htn'); await selectPreset(user, 'stage2-htn')
    second.resolve(evaluation('stage2-result'))
    expect(await screen.findByRole('dialog')).toHaveTextContent('stage2-result')
    first.resolve(evaluation('stage1-result')); await Promise.resolve()
    expect(screen.getByRole('dialog')).toHaveTextContent('stage2-result')
  })

  it('keeps the preset chart open and offers retry after failure', async () => {
    apiMocks.evaluateTree.mockRejectedValueOnce(new Error('Clinical service unavailable'))
      .mockResolvedValueOnce(evaluation('retried-result'))
    const user = userEvent.setup(); render(<ShowcasePage />)
    await selectPreset(user, 'normal-bp')

    expect(await screen.findByRole('alert')).toHaveTextContent('Clinical service unavailable')
    expect(screen.getByRole('main', { name: `${profile('normal-bp').name} chart` })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /Try again/ }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('retried-result')
  })
})

