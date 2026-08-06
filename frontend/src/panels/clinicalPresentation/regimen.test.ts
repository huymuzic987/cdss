import { describe, expect, it } from 'vitest'
import { parseFinalRegimenOptions, parseRegimenPlan } from './regimen'

describe('parseRegimenPlan', () => {
  it('keeps start and add steps separate with independent doses', () => {
    const steps = parseRegimenPlan({
      schema_version: '1.0',
      steps: [
        {
          id: 'start',
          keyword: 'START',
          text_en: 'Start A and C',
          text_vi: 'Start A and C',
          components: [],
          alternatives: [{
            components: [
              { selector_kind: 'class', code: 'A', dose_strategy: 'LOW_DOSE' },
              { selector_kind: 'class', code: 'C', dose_strategy: 'LOW_DOSE' },
            ],
          }],
        },
        {
          id: 'add',
          keyword: 'ADD',
          text_en: 'Add B',
          text_vi: 'Add B',
          components: [
            { selector_kind: 'class', code: 'B', dose_strategy: 'USUAL_DOSE' },
          ],
          alternatives: [],
        },
      ],
    }, 'en')

    expect(steps).toEqual([
      {
        id: 'start',
        treeKey: '',
        nodeKey: '',
        operation: 'START',
        instruction: 'Start A and C',
        componentLabel: 'A + C',
        doseLabel: 'Low dose',
      },
      {
        id: 'add',
        treeKey: '',
        nodeKey: '',
        operation: 'ADD',
        instruction: 'Add B',
        componentLabel: 'B',
        doseLabel: 'Usual dose',
      },
    ])
  })

  it('defaults an unspecified dose to low dose', () => {
    const [step] = parseRegimenPlan({
      schema_version: '1.0',
      steps: [{
        id: 'add',
        keyword: 'ADD',
        text_en: 'Add B',
        text_vi: 'Add B',
        components: [{ selector_kind: 'class', code: 'B' }],
        alternatives: [],
      }],
    }, 'en')

    expect(step?.doseLabel).toBe('Low dose')
  })

  it('expands alternative bases into complete options with every addition', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      effective_regimen: {
        base_options: [
          { components: [{ selector_kind: 'class', code: 'A' }, { selector_kind: 'class', code: 'C' }] },
          { components: [{ selector_kind: 'class', code: 'A' }, { selector_kind: 'class', code: 'D' }] },
        ],
        additions: [{ selector_kind: 'class', code: 'B' }],
      },
    }, 'en')

    expect(options).toEqual([
      {
        id: 'regimen-option-1',
        components: [
          { label: 'A', detail: 'RAS (ACE inhibitor / ARB / ARNI)', group: 'A', dose: 'Low dose' },
          { label: 'C', detail: 'Calcium-channel blocker', group: 'C', dose: 'Low dose' },
          { label: 'B', detail: 'Beta-blocker', group: 'B', dose: 'Low dose' },
        ],
      },
      {
        id: 'regimen-option-2',
        components: [
          { label: 'A', detail: 'RAS (ACE inhibitor / ARB / ARNI)', group: 'A', dose: 'Low dose' },
          { label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose' },
          { label: 'B', detail: 'Beta-blocker', group: 'B', dose: 'Low dose' },
        ],
      },
    ])
  })

  it('removes complete regimens that differ only by component order', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      effective_regimen: {
        base_options: [
          { components: [{ code: 'A' }, { code: 'B' }, { code: 'C' }, { code: 'D' }] },
          { components: [{ code: 'A' }, { code: 'C' }, { code: 'D' }, { code: 'B' }] },
        ],
        additions: [],
      },
    }, 'en')

    expect(options).toHaveLength(1)
    expect(options[0]?.components.map((component) => component.label)).toEqual(['A', 'B', 'C', 'D'])
  })

  it('keeps a SELECT medicine list as separate OR options', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      effective_regimen: {
        base_options: [
          { components: [{ selector_kind: 'medicine', name: 'Methyldopa' }] },
          { components: [{ selector_kind: 'medicine', name: 'Labetalol (oral)' }] },
          { components: [{ selector_kind: 'medicine', name: 'Nifedipine (avoid capsule form)' }] },
          { components: [{ selector_kind: 'medicine', name: 'Nicardipine' }] },
        ],
        additions: [],
      },
    }, 'en')

    expect(options.map((option) => option.components.map((item) => [item.label, item.group]))).toEqual([
      [['Methyldopa', 'Others']],
      [['Labetalol (oral)', 'B']],
      [['Nifedipine (avoid capsule form)', 'C']],
      [['Nicardipine', 'C']],
    ])
  })

  it('deduplicates class codes and class-name aliases into one canonical group', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      effective_regimen: {
        base_options: [{ components: [
          { selector_kind: 'class', code: 'B' },
          { selector_kind: 'class', name: 'Beta-blocker' },
        ] }],
        additions: [],
      },
    }, 'en')

    expect(options[0]?.components).toEqual([
      { label: 'B', detail: 'Beta-blocker', group: 'B', dose: 'Low dose' },
    ])
  })

  it('preserves subgroup detail from structured class names', () => {
    const catalog = {
      A: [
        { id: 'ace', name: 'ACE', group: 'A', subgroup: 'UCMC', route: '', doseLow: '', doseUsual: '', doseMax: '', snomedCode: '' },
        { id: 'arb', name: 'ARB', group: 'A', subgroup: 'CTTA', route: '', doseLow: '', doseUsual: '', doseMax: '', snomedCode: '' },
      ],
      C: [
        { id: 'dhp', name: 'DHP', group: 'C', subgroup: 'CKCa DHP', route: '', doseLow: '', doseUsual: '', doseMax: '', snomedCode: '' },
        { id: 'non-dhp', name: 'Non-DHP', group: 'C', subgroup: 'CKCa Non-DHP', route: '', doseLow: '', doseUsual: '', doseMax: '', snomedCode: '' },
      ],
    }
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      effective_regimen: {
        base_options: [
          { components: [
            { selector_kind: 'class', code: 'A', name: 'A (ARNI or CTTA or UCMC)' },
            { selector_kind: 'class', code: 'C', name: 'Dihydropyridine CCB' },
          ] },
          { components: [
            { selector_kind: 'class', code: 'A', name: 'A (ARNI or CTTA or UCMC)' },
            { selector_kind: 'class', code: 'C', name: 'Non-DHP CCB' },
          ] },
        ],
        additions: [],
      },
    }, 'en', catalog)

    expect(options.map((option) => option.components)).toEqual([
      [
        {
          label: 'A', detail: 'RAS (ACE inhibitor / ARB / ARNI)', group: 'A',
          dose: 'Low dose', subgroup: 'UCMC / CTTA',
        },
        { label: 'C', detail: 'Calcium-channel blocker', group: 'C', dose: 'Low dose', subgroup: 'CKCa DHP' },
      ],
      [
        {
          label: 'A', detail: 'RAS (ACE inhibitor / ARB / ARNI)', group: 'A',
          dose: 'Low dose', subgroup: 'UCMC / CTTA',
        },
        { label: 'C', detail: 'Calcium-channel blocker', group: 'C', dose: 'Low dose', subgroup: 'CKCa Non-DHP' },
      ],
    ])
  })

  it('uses MRA as a separate group and prioritizes a specific medicine name', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      effective_regimen: {
        base_options: [{ components: [
          { selector_kind: 'class', code: 'MRA' },
          { selector_kind: 'medicine', name: 'Spironolactone' },
        ] }],
        additions: [],
      },
    }, 'en')

    expect(options[0]?.components).toEqual([
      { label: 'Spironolactone', detail: 'MRA', group: 'MRA', dose: 'Low dose' },
    ])
  })

  it('normalizes legacy SGLT2i and GLP1RA class aliases into separate groups', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      effective_regimen: {
        base_options: [{ components: [
          { selector_kind: 'class', code: 'SGLT2_INHIBITOR' },
          { selector_kind: 'class', code: 'GLP1_RECEPTOR_AGONIST' },
        ] }],
        additions: [],
      },
    }, 'en')

    expect(options[0]?.components).toEqual([
      { label: 'SGLT2i', detail: 'SGLT2 inhibitor', group: 'SGLT2i', dose: 'Low dose' },
      { label: 'GLP1RA', detail: 'GLP-1 receptor agonist', group: 'GLP1RA', dose: 'Low dose' },
    ])
  })

  it('uses the last material adjustment when the effective state has no base', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      steps: [{
        id: 'escalate',
        keyword: 'ESCALATE',
        components: [{ selector_kind: 'class', code: 'A' }, { selector_kind: 'class', code: 'C' }],
        alternatives: [],
      }],
      effective_regimen: {
        base_options: [],
        additions: [],
        adjustments: [],
      },
    }, 'en')

    expect(options[0]?.components.map((component) => component.label)).toEqual(['A', 'C'])
  })

  it('does not recreate removed components from the final REMOVE step', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      steps: [{
        id: 'remove',
        keyword: 'REMOVE',
        components: [
          { selector_kind: 'class', code: 'B' },
          { selector_kind: 'class', code: 'C' },
        ],
        alternatives: [],
      }],
      effective_regimen: {
        base_options: [],
        additions: [],
        stopped_components: [
          { selector_kind: 'class', code: 'B' },
          { selector_kind: 'class', code: 'C' },
        ],
      },
    }, 'en')

    expect(options).toEqual([])
  })

  it('keeps a D option when only a D subgroup is stopped', () => {
    const options = parseFinalRegimenOptions({
      schema_version: '1.0',
      steps: [{
        id: 'remove-thiazide',
        keyword: 'REMOVE',
        text_en: 'Remove D (LT Thiazide)',
        components: [{ selector_kind: 'class', code: 'D', subgroup: 'LT Thiazide' }],
        alternatives: [],
      }],
      effective_regimen: {
        base_options: [
          { components: [{ selector_kind: 'class', code: 'A' }, { selector_kind: 'class', code: 'D' }] },
        ],
        additions: [],
        stopped_components: [{ selector_kind: 'class', code: 'D', subgroup: 'LT Thiazide' }],
      },
    }, 'en')

    expect(options[0]?.components.map((component) => component.label)).toEqual(['A', 'D'])
  })

  it('shows the removed subgroup in a REMOVE step', () => {
    const [step] = parseRegimenPlan({
      schema_version: '1.0',
      steps: [{
        id: 'remove-thiazide',
        keyword: 'REMOVE',
        text_en: 'Remove matched contraindicated drug groups: D (LT Thiazide)',
        text_vi: 'Loại bỏ: D (LT Thiazide)',
        components: [{ selector_kind: 'class', code: 'D', subgroup: 'LT Thiazide' }],
        alternatives: [],
      }],
    }, 'en')

    expect(step?.componentLabel).toBe('D (LT Thiazide)')
    expect(step?.instruction).toContain('D (LT Thiazide)')
  })
})
