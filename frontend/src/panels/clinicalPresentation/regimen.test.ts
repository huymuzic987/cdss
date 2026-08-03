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
        operation: 'START',
        instruction: 'Start A and C',
        componentLabel: 'A + C',
        doseLabel: 'Low dose',
      },
      {
        id: 'add',
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
})
