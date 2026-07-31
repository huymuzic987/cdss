// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { JsonObject } from '../api/types'
import { MockPatientSidebar } from './MockPatientSidebar'

afterEach(cleanup)

function renderSidebar() {
  const onStart = vi.fn()
  const onManualStart = vi.fn()
  render(
    <MockPatientSidebar
      isRunning={false}
      canReset={true}
      onStart={onStart}
      onManualStart={onManualStart}
      onReset={vi.fn()}
      theme="light"
      onToggleTheme={vi.fn()}
    />,
  )
  fireEvent.change(screen.getByLabelText('Preset Patient'), {
    target: { value: 'pregnancy-episode-follow-up-3' },
  })
  return { onStart, onManualStart }
}

function encounterCount(bundle: JsonObject): number {
  const entries = Array.isArray(bundle.entry) ? bundle.entry as JsonObject[] : []
  return entries.filter(
    (entry) => (entry.resource as JsonObject | undefined)?.resourceType === 'Encounter',
  ).length
}

describe('pregnancy longitudinal presets', () => {
  it('passes all four encounters to automatic traversal', () => {
    const { onStart } = renderSidebar()

    fireEvent.click(screen.getByRole('button', { name: /Start Traversal/ }))

    expect(onStart).toHaveBeenCalledOnce()
    expect(onStart.mock.calls[0][0]).toBe('hypertension-diagnosis')
    expect(encounterCount(onStart.mock.calls[0][1])).toBe(4)
  })

  it('passes the same four-encounter Bundle to manual traversal', () => {
    const { onManualStart } = renderSidebar()

    fireEvent.click(screen.getByRole('button', { name: /Manual Traverse/ }))

    expect(onManualStart).toHaveBeenCalledOnce()
    expect(onManualStart.mock.calls[0][0]).toBe('hypertension-diagnosis')
    expect(encounterCount(onManualStart.mock.calls[0][1])).toBe(4)
  })
})
