// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RegimenComponentSummary } from './RegimenComponentSummary'

describe('compact regimen component summaries', () => {
  it('hides group and subgroup clarification for a medicine row item', () => {
    render(<RegimenComponentSummary
      locale="en"
      kind="medicine"
      label="Bisoprolol"
      compactLabel="Bisoprolol"
      clarification="Beta-blockers"
      subgroups="Subgroups: Beta-blocker"
      dose="1.25 mg"
      inline
      compact
    />)

    expect(screen.getByText('Bisoprolol')).toBeTruthy()
    expect(screen.getByText('1.25 mg')).toBeTruthy()
    expect(screen.queryByText('Beta-blockers')).toBeNull()
    expect(screen.queryByText('Subgroups: Beta-blocker')).toBeNull()
  })
})
