// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { ClinicalSection } from './ClinicalSection'

afterEach(cleanup)

describe('ClinicalSection', () => {
  it('uses a consistent icon and preserves native disclosure behavior', async () => {
    render(<ClinicalSection title="Clinical plan" defaultOpen={false}>Content</ClinicalSection>)
    const summary = screen.getByText('Clinical plan').closest('summary')!
    const details = summary.closest('details')!

    expect(summary.querySelector('.cds-section-chevron svg')).toBeTruthy()
    expect(details.open).toBe(false)
    await userEvent.setup().click(summary)
    expect(details.open).toBe(true)
  })
})

