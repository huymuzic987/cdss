import { describe, expect, it } from 'vitest'
import { singleDrugGroupDisplay } from './drugClassLabels'

describe('singleDrugGroupDisplay', () => {
  it.each([
    ['Enalapril', 'A', 'A · RAS inhibitors'],
    ['Losartan', 'A', 'A · RAS inhibitors'],
    ['Amlodipine', 'C', 'C · Calcium channel blockers'],
    ['Furosemide', 'D', 'D · Diuretics'],
    ['Methyldopa', 'Chủ vận chọn lọc alpha-2 giao cảm', 'Centrally acting antihypertensive'],
  ])('maps %s from its catalog group', (medicine, catalogGroup, expected) => {
    expect(singleDrugGroupDisplay(medicine, catalogGroup, 'en')).toBe(expected)
  })

  it('does not present Methyldopa itself as a drug group', () => {
    expect(singleDrugGroupDisplay(
      'Methyldopa',
      'Chủ vận chọn lọc alpha-2 giao cảm',
      'en',
    )).not.toBe('Methyldopa')
  })
})
