import { describe, expect, it } from 'vitest'
import { componentSummary } from './regimenComponentPresentation'

describe('regimen component presentation', () => {
  it('uses the same current subgroup set as the group details popup', () => {
    const summary = componentSummary({ label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose' }, {
      D: [{ id: 'loop', name: 'Furosemide', group: 'D', subgroup: 'Loop diuretic', route: '', doseLow: '20 mg', doseUsual: '40 mg', doseMax: '80 mg', snomedCode: '' }],
    }, 'en')

    expect(summary.clarification).toBe('Diuretics')
    expect(summary.subgroups).toContain('Loop diuretic')
    expect(summary.subgroups).not.toContain('Thiazide')
  })

  it('does not display a removed subgroup from a stale component selector', () => {
    const summary = componentSummary({ label: 'D', detail: 'Diuretic', group: 'D', subgroup: 'Thiazide / Thiazide-like', dose: 'Low dose' }, {
      D: [{ id: 'loop', name: 'Furosemide', group: 'D', subgroup: 'Loop diuretic', route: '', doseLow: '20 mg', doseUsual: '40 mg', doseMax: '80 mg', snomedCode: '' }],
    }, 'en')

    expect(summary.subgroups).toBe('No current subgroups')
  })
})
