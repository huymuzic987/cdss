import { describe, expect, it } from 'vitest'
import { isSingleMedicationOrder } from './orderClassification'

describe('isSingleMedicationOrder', () => {
  it('accepts a medication order without an ABCD combination', () => {
    expect(isSingleMedicationOrder({ orderType: 'medication', drugClasses: [{ code: 'A' }] })).toBe(true)
    expect(isSingleMedicationOrder({ orderType: 'medication', drugClasses: [{ code: 'ARB' }, { code: 'CCB' }] })).toBe(true)
  })

  it('rejects current regimens and ABCD combination therapy', () => {
    expect(isSingleMedicationOrder({ orderType: 'current-regimen', drugClasses: [{ code: 'A' }] })).toBe(false)
    expect(isSingleMedicationOrder({ orderType: 'medication', drugClasses: [{ code: 'A' }, { code: 'C' }] })).toBe(false)
  })
})
