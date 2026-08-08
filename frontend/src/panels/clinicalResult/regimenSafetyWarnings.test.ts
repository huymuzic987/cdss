import { describe, expect, it } from 'vitest'
import type { CatalogGroup, EvaluationResponse, JsonObject } from '../../api/types'
import type { ClinicalPresentation, FinalRegimenComponent } from '../clinicalPresentation/types'
import { createRegimenSafetyWarningResolver } from './regimenSafetyWarnings'

const medicine = {
  drug_id: 'hydrochlorothiazide', name: 'Hydrochlorothiazide', group_code: 'D', subgroup: 'Thiazide',
  route: 'Oral', dose_low: '12.5 mg', dose_usual: '25 mg', dose_max: '50 mg', available: true, snomed_code: null,
}
const catalog: CatalogGroup[] = [{ code: 'D', label_en: 'Diuretic', label_vi: 'Lợi tiểu', subgroups: [{ name: 'Thiazide', medicines: [medicine] }] }]
const component: FinalRegimenComponent = { label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose', selectorKind: 'group' }
const presentation = { regimenCatalog: {} } as ClinicalPresentation

function resultWithProfile(profile: JsonObject): EvaluationResponse {
  return { context: { medication_safety: profile }, actions: [] } as unknown as EvaluationResponse
}

describe('regimen safety warnings', () => {
  it('marks an absolute contraindication without blocking the component', () => {
    const warnings = createRegimenSafetyWarningResolver(catalog, presentation, resultWithProfile({ findings: [{ target: 'THIAZIDE_LIKE_DIURETIC', severity: 'ABSOLUTE', reason_en: 'Gout' }] }), 'en')(component)

    expect(warnings[0]).toMatchObject({ severity: 'ABSOLUTE', text: 'Absolute contraindication: Gout' })
  })

  it('keeps relative and incomplete safety findings as review warnings', () => {
    const relativeWarnings = createRegimenSafetyWarningResolver(catalog, {
      regimenCatalog: { D: [{ id: medicine.drug_id, name: medicine.name, group: 'D', subgroup: 'Thiazide', route: 'Oral', doseLow: '12.5 mg', doseUsual: '25 mg', doseMax: '50 mg', snomedCode: '', safetyStatus: 'RELATIVE' }] },
    } as unknown as ClinicalPresentation, resultWithProfile({}), 'en')(component)
    const incompleteWarnings = createRegimenSafetyWarningResolver([{ ...catalog[0]!, code: 'MRA', subgroups: [{ ...catalog[0]!.subgroups[0]!, medicines: [{ ...medicine, group_code: 'MRA', drug_id: 'spironolactone', name: 'Spironolactone' }] }] }], presentation, resultWithProfile({ findings: [{ target: 'MRA', severity: 'INSUFFICIENT_DATA' }] }), 'en')({ ...component, group: 'MRA' })

    expect(relativeWarnings[0]?.severity).toBe('RELATIVE')
    expect(incompleteWarnings[0]?.severity).toBe('INSUFFICIENT_DATA')
  })
})
