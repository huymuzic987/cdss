import { describe, expect, it } from 'vitest'
import type { CriticalSummary } from './criticalSummaryTypes'
import { deriveCareActions } from './careActions'

describe('deriveCareActions resistant-hypertension checks', () => {
  it('keeps tolerance checks out of the clinical plan', () => {
    const summary: CriticalSummary = {
      urgency: 'routine',
      urgencyLabel: 'Routine',
      findings: [],
      followUp: null,
      path: [
        {
          id: 'resistant-hypertension:T13_A_CHECK_MRA',
          label: 'Check MRA tolerance',
          treeName: 'Resistant hypertension',
          kind: 'treatment',
        },
        {
          id: 'resistant-hypertension:T13_A_CHECK_SPIRONOLACTONE',
          label: 'Check spironolactone tolerance',
          treeName: 'Resistant hypertension',
          kind: 'treatment',
        },
        {
          id: 'resistant-hypertension:T13_A_CONSIDER_DEVICE',
          label: 'Consider device treatment',
          treeName: 'Resistant hypertension',
          kind: 'treatment',
        },
      ],
    }

    expect(deriveCareActions('', [], summary, {
      treatment: { tolerates_mra: true, tolerates_spironolactone: false },
    })).toEqual(['Consider device treatment'])
  })
})
