import { describe, expect, it } from 'vitest'
import type { CatalogGroup } from '../../api/types'
import { editorComponentSummary } from './regimenEditorUtils'

const catalog: CatalogGroup[] = [{
  code: 'D',
  label_en: 'Diuretics',
  label_vi: 'Lợi tiểu',
  subgroups: [
    { name: 'LT Thiazide', medicines: [] },
    { name: 'LT Thiazide-like', medicines: [] },
    { name: 'LT quai', medicines: [] },
    { name: 'LT giữ Kali', medicines: [] },
  ],
}]

const medicineCatalog: CatalogGroup[] = [{
  code: 'B',
  label_en: 'Beta-blocker',
  label_vi: 'Chẹn beta',
  subgroups: [{ name: 'Beta-blocker', medicines: [{
    drug_id: 'labetalol', name: 'Labetalol', group_code: 'B', subgroup: 'Beta-blocker',
    route: 'Oral', dose_low: '100 mg', dose_usual: '200 mg', dose_max: '400 mg', available: true, snomed_code: null,
  }] }],
}]

describe('regimen editor component summaries', () => {
  it('keeps a custom subgroup selection exact when similar subgroup names exist', () => {
    const summary = editorComponentSummary({
      label: 'Diuretics',
      detail: 'LT quai / LT giữ Kali / LT Thiazide-like',
      group: 'D',
      dose: 'Low dose',
      subgroup: 'LT quai / LT giữ Kali / LT Thiazide-like',
      selectorKind: 'subgroup',
      isCustom: true,
    }, catalog, 'en', {
      D: ['LT Thiazide', 'LT Thiazide-like', 'LT quai', 'LT giữ Kali'],
    })

    expect(summary.subgroups).toBe('Subgroups: LT Thiazide-like / LT quai / LT giữ Kali')
    expect(summary.subgroups).not.toContain('LT Thiazide /')
  })

  it('keeps a named medicine as a medicine when its id is absent', () => {
    const summary = editorComponentSummary({
      label: 'Labetalol', detail: 'Beta-blocker', group: 'B', dose: 'Low dose',
    }, medicineCatalog, 'en')

    expect(summary.kind).toBe('medicine')
    expect(summary.label).toBe('Labetalol')
    expect(summary.dose).toBe('100 mg')
  })
})
