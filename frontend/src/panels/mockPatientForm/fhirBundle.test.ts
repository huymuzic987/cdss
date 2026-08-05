import { describe, expect, it } from 'vitest'
import { PATIENT_PRESETS } from '../patientPresets'
import {
  CONTRAINDICATION,
  FOLLOW_UP,
  PREGNANCY,
  PREGNANCY_FOLLOW_UP,
} from '../patientPresets/shared'
import { bundleToForm, formToPayload } from './payload'
import { bundleToFlat } from './fhirBundle'
import { validatePatientForm } from './validation'

const medicationEpisodePrefix = /^(?:med-review-episode|comorbidity-episode-.+)-follow-up-/

function expectedMedicationOutcome(flat: Record<string, unknown>) {
  const sbp = Number(flat.current_clinic_sbp)
  const dbp = Number(flat.current_clinic_dbp)
  const targetSbp = Number(flat.active_bp_target_sbp_upper)
  const targetDbp = Number(flat.active_bp_target_dbp_upper)
  if (sbp < targetSbp && dbp < targetDbp) return 'MAINTAIN_CONTROLLED'
  if (flat.drug_replacement_required === true) return 'REPLACE_DRUG_SAME_STAGE'

  const assessment = Date.parse(String(flat.assessment_date))
  const effective = Date.parse(String(flat.regimen_effective_date))
  const elapsedDays = (assessment - effective) / 86_400_000
  if (elapsedDays < Number(flat.minimum_regimen_days)) return 'CONTINUE_UNTIL_REASSESSMENT'
  if (flat.adherence_adequate === false || flat.dose_adequate === false) {
    return 'ADDRESS_ADHERENCE_OR_DOSE'
  }
  return 'ESCALATE_REGIMEN'
}

describe('canonical FHIR patient presets', () => {
  it.each(PATIENT_PRESETS.map((preset) => [preset.id, preset] as const))(
    '%s is stored and round-trips as a canonical clinical Bundle',
    (_id, preset) => {
      expect(preset.bundle.resourceType).toBe('Bundle')
      expect(preset.bundle.type).toBe('collection')
      const entries = Array.isArray(preset.bundle.entry) ? preset.bundle.entry : []
      const resources = entries.map((entry) => (entry as { resource?: { resourceType?: string } }).resource)
      expect(resources.filter((resource) => resource?.resourceType === 'Patient')).toHaveLength(1)
      expect(resources.some((resource) => resource?.resourceType === 'Parameters')).toBe(false)

      const rebuilt = formToPayload(bundleToForm(preset.bundle), `preset-${preset.id}`)
      expect(rebuilt.resourceType).toBe('Bundle')
      const rebuiltEntries = Array.isArray(rebuilt.entry) ? rebuilt.entry : []
      expect(rebuiltEntries.some((entry) => (entry as { resource?: { resourceType?: string } }).resource?.resourceType === 'Patient')).toBe(true)
    },
  )

  it('gives every contraindication preset both clinic and home blood pressure readings', () => {
    const presets = PATIENT_PRESETS.filter(({ category }) => category === CONTRAINDICATION)
    expect(presets).toHaveLength(20)

    for (const preset of presets) {
      const entries = preset.bundle.entry as Array<{ resource: Record<string, unknown> }>
      const observations = entries
        .map(({ resource }) => resource)
        .filter((resource) => resource.resourceType === 'Observation')
      const roles = observations.map((resource) => {
        const extensions = resource.extension as Array<{ url?: string, valueCode?: string }> | undefined
        return extensions?.find(({ url }) => url?.endsWith('/reading-role'))?.valueCode
      })

      expect(roles, preset.id).toContain('current_clinic')
      expect(roles, preset.id).toContain('home')
      expect(bundleToFlat(preset.bundle).home_sbp, preset.id).not.toBeUndefined()
      expect(bundleToFlat(preset.bundle).home_dbp, preset.id).not.toBeUndefined()
    }
  })

  it('layers contraindication findings onto copied working presets', () => {
    const preset = PATIENT_PRESETS.find(({ id }) => id === 'contra-03-pregnancy-thiazide')
    expect(preset).toBeDefined()
    const entries = preset!.bundle.entry as Array<{ resource: Record<string, any> }>
    const patient = entries.find(({ resource }) => resource.resourceType === 'Patient')!.resource
    const pregnancy = entries.find(({ resource }) => resource.id?.endsWith('-cond-pregnancy'))!.resource
    const medications = entries.filter(({ resource }) => resource.resourceType === 'MedicationRequest')
    const input = (patient.extension as Array<Record<string, any>>).find(({ url }) => url.endsWith('/is_pregnant'))

    expect(input?.valueBoolean).toBe(true)
    expect(bundleToFlat(preset!.bundle).has_hypertension_after_week_20).toBe(true)
    expect(bundleToFlat(preset!.bundle).weeks_persisting_postpartum).toBe(0)
    expect(bundleToFlat(preset!.bundle).proteinuria_24h_mg).toBe(0)
    expect(bundleToFlat(preset!.bundle).acr_mg_mmol).toBe(0)
    expect(pregnancy.code.coding).toEqual(expect.arrayContaining([
      expect.objectContaining({ code: 'Z32' }),
      expect.objectContaining({ code: '77386006' }),
    ]))
    expect(medications.some(({ resource }) => resource.medicationCodeableConcept?.text === 'CHLORTHALIDONE')).toBe(true)
    expect(bundleToFlat(preset!.bundle).is_pregnant).toBe(true)
  })

  it('gives every pregnancy contraindication bundle a usable hypertension classification', () => {
    const pregnancyContraindications = PATIENT_PRESETS.filter(
      ({ category, id }) => category === CONTRAINDICATION && id.includes('pregnancy'),
    )

    expect(pregnancyContraindications).toHaveLength(4)
    for (const preset of pregnancyContraindications) {
      const flat = bundleToFlat(preset.bundle)
      expect(flat.is_pregnant, preset.id).toBe(true)
      expect(flat.has_hypertension_after_week_20, preset.id).toBe(true)
      expect(flat.home_sbp, preset.id).not.toBeUndefined()
      expect(flat.home_dbp, preset.id).not.toBeUndefined()
      expect(flat.proteinuria_24h_mg, preset.id).toBe(0)
      expect(flat.acr_mg_mmol, preset.id).toBe(0)
    }
  })

  it('keeps every contraindication bundle valid for the same form workflow', () => {
    for (const preset of PATIENT_PRESETS.filter(({ category }) => category === CONTRAINDICATION)) {
      const form = bundleToForm(preset.bundle)
      const validation = validatePatientForm(form)
      expect(validation.error, preset.id).toBeNull()
    }
  })

  it('keeps aspirin prophylaxis as a normotensive high-risk follow-up', () => {
    const preset = PATIENT_PRESETS.find(
      ({ id }) => id === 'pregnancy-high-preeclampsia-risk-aspirin',
    )
    expect(preset).toBeDefined()
    const form = bundleToForm(preset!.bundle)

    expect(form.current_clinic_sbp).toBe('130')
    expect(form.current_clinic_dbp).toBe('80')
    expect(form.has_high_preeclampsia_risk).toBe(true)
    expect(form.has_hypertension_after_week_20).toBe(true)
    const entries = preset!.bundle.entry as Array<{ resource: { resourceType: string } }>
    expect(entries.filter(({ resource }) => resource.resourceType === 'Encounter')).toHaveLength(2)
  })

  it('keeps Active BP Target populated for every known-stage medication follow-up preset', () => {
    const knownStagePresets = PATIENT_PRESETS.filter((preset) => preset.category === FOLLOW_UP)
      .map((preset) => ({ preset, form: bundleToForm(preset.bundle) }))
      .filter(({ form }) => form.medication_follow_up_stage !== '')
    expect(knownStagePresets.length).toBeGreaterThan(0)

    for (const { preset, form } of knownStagePresets) {
      expect(form.target_sbp_upper, `${preset.id} target_sbp_upper`).not.toBe('')
      expect(form.target_dbp_upper, `${preset.id} target_dbp_upper`).not.toBe('')
      const validation = validatePatientForm(form)
      expect(validation.error, `${preset.id}: ${validation.error}`).toBeNull()
    }
  })

  it('stores explicit drug-class combinations in medication episode Bundles', () => {
    const expected = new Map([
      ['med-review-episode-follow-up-1-replace', 'A+D'],
      ['med-review-episode-follow-up-2-escalate', 'A+D'],
      ['med-review-episode-follow-up-3-early', 'A+C+D'],
      ['med-review-episode-follow-up-4-controlled', 'A+C+D'],
    ])
    for (const [id, combination] of expected) {
      const preset = PATIENT_PRESETS.find((candidate) => candidate.id === id)
      expect(preset, id).toBeDefined()
      const flat = bundleToForm(preset!.bundle)
      const patient = (preset!.bundle.entry as Array<{ resource: Record<string, unknown> }>)
        .find(({ resource }) => resource.resourceType === 'Patient')!.resource
      const extensions = patient.extension as Array<{ url: string, valueString?: string }>
      expect(extensions.find(({ url }) => url.endsWith('/current_regimen_drug_classes'))?.valueString)
        .toBe(combination)
      expect(flat.current_regimen_drug_classes).toBe(combination)
      expect(flat.medication_follow_up_stage).not.toBe('')
    }
  })

  it('makes every medication episode follow-up independently evaluable from its FHIR Bundle', () => {
    const followUps = PATIENT_PRESETS.filter(({ id }) => medicationEpisodePrefix.test(id))
    expect(followUps.length).toBeGreaterThan(0)

    for (const preset of followUps) {
      const flat = bundleToFlat(preset.bundle)
      const required = [
        'current_clinic_sbp', 'current_clinic_dbp',
        'active_bp_target_sbp_upper', 'active_bp_target_dbp_upper',
        'medication_follow_up_stage', 'current_regimen_drug_classes', 'assessment_date',
        'regimen_effective_date', 'minimum_regimen_days',
      ]
      for (const field of required) {
        expect(flat[field], `${preset.id}: ${field}`).not.toBeUndefined()
        expect(flat[field], `${preset.id}: ${field}`).not.toBe('')
      }
      expect(flat.is_medication_follow_up, preset.id).toBe(true)

      // Reading this one Bundle supplies every gate input; no earlier episode
      // or patient checkpoint is consulted by the decoder.
      expect(expectedMedicationOutcome(flat), preset.id).toBeTruthy()
    }
  })

  const medicationEpisodeOutcomes = [
    ['med-review-episode-follow-up-1-replace', 'REPLACE_DRUG_SAME_STAGE'],
    ['med-review-episode-follow-up-2-escalate', 'ESCALATE_REGIMEN'],
    ['med-review-episode-follow-up-3-early', 'CONTINUE_UNTIL_REASSESSMENT'],
    ['med-review-episode-follow-up-4-controlled', 'MAINTAIN_CONTROLLED'],
    ['comorbidity-episode-ckd-follow-up-1-replace', 'REPLACE_DRUG_SAME_STAGE'],
    ['comorbidity-episode-ckd-follow-up-2-escalate', 'ESCALATE_REGIMEN'],
    ['comorbidity-episode-ckd-follow-up-3-controlled', 'MAINTAIN_CONTROLLED'],
    ['comorbidity-episode-type2-diabetes-follow-up-1-early', 'CONTINUE_UNTIL_REASSESSMENT'],
    ['comorbidity-episode-type2-diabetes-follow-up-2-controlled', 'MAINTAIN_CONTROLLED'],
    ['comorbidity-episode-type2-diabetes-follow-up-3-maintain', 'MAINTAIN_CONTROLLED'],
    ['comorbidity-episode-cad-follow-up-1-address-adherence', 'ADDRESS_ADHERENCE_OR_DOSE'],
    ['comorbidity-episode-cad-follow-up-2-escalate', 'ESCALATE_REGIMEN'],
    ['comorbidity-episode-cad-follow-up-3-controlled', 'MAINTAIN_CONTROLLED'],
    ['comorbidity-episode-heart-failure-follow-up-1-early', 'CONTINUE_UNTIL_REASSESSMENT'],
    ['comorbidity-episode-heart-failure-follow-up-2-escalate', 'ESCALATE_REGIMEN'],
    ['comorbidity-episode-heart-failure-follow-up-3-controlled', 'MAINTAIN_CONTROLLED'],
    ['comorbidity-episode-older-adult-follow-up-1-replace', 'REPLACE_DRUG_SAME_STAGE'],
    ['comorbidity-episode-older-adult-follow-up-2-escalate', 'ESCALATE_REGIMEN'],
    ['comorbidity-episode-older-adult-follow-up-3-controlled', 'MAINTAIN_CONTROLLED'],
    ['comorbidity-episode-resistant-hypertension-follow-up-1-increase-dose', 'ADDRESS_ADHERENCE_OR_DOSE'],
    ['comorbidity-episode-resistant-hypertension-follow-up-2-replace-drug', 'REPLACE_DRUG_SAME_STAGE'],
    ['comorbidity-episode-resistant-hypertension-follow-up-3-address-adherence', 'ADDRESS_ADHERENCE_OR_DOSE'],
    ['comorbidity-episode-resistant-hypertension-follow-up-4-use-three-drugs', 'ESCALATE_REGIMEN'],
    ['comorbidity-episode-resistant-hypertension-follow-up-5-early', 'CONTINUE_UNTIL_REASSESSMENT'],
    ['comorbidity-episode-resistant-hypertension-follow-up-6-resistant-bp-check', 'ESCALATE_REGIMEN'],
    ['comorbidity-episode-resistant-hypertension-follow-up-7-resistant-bp-check', 'ESCALATE_REGIMEN'],
  ] as const

  it.each(medicationEpisodeOutcomes)(
    '%s contains the FHIR inputs for %s before traversal',
    (id, outcome) => {
      const preset = PATIENT_PRESETS.find((candidate) => candidate.id === id)
      expect(preset, id).toBeDefined()
      expect(expectedMedicationOutcome(bundleToFlat(preset!.bundle))).toBe(outcome)
    },
  )

  it('has an explicit expected gate outcome for every medication episode follow-up', () => {
    const actualIds = PATIENT_PRESETS
      .filter(({ id }) => medicationEpisodePrefix.test(id))
      .map(({ id }) => id)
      .sort()
    const expectedIds = medicationEpisodeOutcomes.map(([id]) => id).sort()
    expect(expectedIds).toEqual(actualIds)
  })

  it.each([
    ['ckd', 'medication-follow-up-ckd-001', 'has_ckd'],
    ['type2-diabetes', 'medication-follow-up-type2-diabetes-001', 'has_type_2_diabetes'],
    ['cad', 'medication-follow-up-cad-001', 'has_coronary_artery_disease'],
    ['heart-failure', 'medication-follow-up-heart-failure-001', 'has_heart_failure'],
  ])('keeps the %s comorbidity episode longitudinal and clinically flagged', (slug, patientId, flag) => {
    const episode = PATIENT_PRESETS.filter(({ id }) => id.startsWith(`comorbidity-episode-${slug}-`))
    expect(episode).toHaveLength(4)
    expect(episode.filter(({ id }) => id.endsWith('-initial'))).toHaveLength(1)
    expect(episode.filter(({ id }) => id.includes('-follow-up-'))).toHaveLength(3)

    for (const preset of episode) {
      const entries = preset.bundle.entry as Array<{ resource: Record<string, unknown> }>
      const patient = entries.find(({ resource }) => resource.resourceType === 'Patient')!.resource
      expect(patient.id).toBe(patientId)
      expect(bundleToForm(preset.bundle)[flag as keyof ReturnType<typeof bundleToForm>]).toBe(true)
    }
  })

  it.each([
    ['older-adult', 'medication-follow-up-older-adult-001'],
  ])('keeps the %s episode on one patient across one initial and three follow-ups', (slug, patientId) => {
    const episode = PATIENT_PRESETS.filter(({ id }) => id.startsWith(`comorbidity-episode-${slug}-`))
    expect(episode).toHaveLength(4)
    expect(episode.filter(({ id }) => id.endsWith('-initial'))).toHaveLength(1)
    expect(episode.filter(({ id }) => id.includes('-follow-up-'))).toHaveLength(3)

    for (const preset of episode) {
      const entries = preset.bundle.entry as Array<{ resource: Record<string, unknown> }>
      const patient = entries.find(({ resource }) => resource.resourceType === 'Patient')!.resource
      expect(patient.id).toBe(patientId)
    }
  })

  it('keeps the resistant-hypertension progression on one patient across all seven follow-ups', () => {
    const episode = PATIENT_PRESETS.filter(
      ({ id }) => id.startsWith('comorbidity-episode-resistant-hypertension-'),
    )
    expect(episode).toHaveLength(8)
    expect(episode.filter(({ id }) => id.endsWith('-initial'))).toHaveLength(1)
    expect(episode.filter(({ id }) => id.includes('-follow-up-'))).toHaveLength(7)

    for (const preset of episode) {
      const entries = preset.bundle.entry as Array<{ resource: Record<string, unknown> }>
      const patient = entries.find(({ resource }) => resource.resourceType === 'Patient')!.resource
      expect(patient.id).toBe('medication-follow-up-resistant-hypertension-001')
    }

    const followUpForm = (number: number, suffix: string) => bundleToForm(
      PATIENT_PRESETS.find(({ id }) => id === (
        `comorbidity-episode-resistant-hypertension-follow-up-${number}-${suffix}`
      ))!.bundle,
    )
    const followUpFlag = (number: number, suffix: string, flag: string) => {
      const preset = PATIENT_PRESETS.find(({ id }) => id === (
        `comorbidity-episode-resistant-hypertension-follow-up-${number}-${suffix}`
      ))!
      return bundleToFlat(preset.bundle)[flag]
    }
    expect(followUpFlag(1, 'increase-dose', 'dose_adequate')).toBe(false)
    expect(followUpFlag(2, 'replace-drug', 'drug_replacement_required')).toBe(true)
    expect(followUpFlag(3, 'address-adherence', 'adherence_adequate')).toBe(false)
    expect(followUpForm(4, 'use-three-drugs').medication_follow_up_stage).toBe('INITIAL_REGIMEN')
    expect(followUpForm(5, 'early').medication_follow_up_stage).toBe('ESCALATED_REGIMEN')
  })

  it('configures resistant follow-up 6 to add MRA and follow-up 7 to reassess it', () => {
    const preset = PATIENT_PRESETS.find(
      ({ id }) => id === 'comorbidity-episode-resistant-hypertension-follow-up-6-resistant-bp-check',
    )
    expect(preset).toBeDefined()
    const form = bundleToForm(preset!.bundle)
    expect(form.facility_capability).toBe('LIMITED_RESOURCES')
    expect(form.medication_follow_up_stage).toBe('ESCALATED_REGIMEN')
    expect(form.current_regimen_drug_classes).toBe('A+C+D')
    expect(bundleToFlat(preset!.bundle).current_regimen_drug_count).toBe(3)
    expect(form.tolerates_mra).toBe(true)

    const reassessment = PATIENT_PRESETS.find(
      ({ id }) => id === 'comorbidity-episode-resistant-hypertension-follow-up-7-resistant-bp-check',
    )
    expect(reassessment).toBeDefined()
    const reassessmentFlat = bundleToFlat(reassessment!.bundle)
    expect(reassessmentFlat.current_regimen_drug_count).toBe(4)
    expect(reassessmentFlat.regimen_effective_date).toBe('2027-02-21')
    expect(reassessmentFlat.assessment_date).toBe('2027-03-21')
  })

  it.each([
    ['heart-failure-follow-up-3-controlled', 4, 'A+B+C+D'],
    ['older-adult-follow-up-1-replace', 1, 'A'],
    ['older-adult-follow-up-2-escalate', 1, 'A'],
  ])('keeps the current regimen accurate for %s', (suffix, count, classes) => {
    const preset = PATIENT_PRESETS.find(
      ({ id }) => id === `comorbidity-episode-${suffix}`,
    )
    expect(preset).toBeDefined()
    const flat = bundleToFlat(preset!.bundle)
    expect(flat.current_regimen_drug_count).toBe(count)
    expect(flat.current_regimen_drug_classes).toBe(classes)
  })

  it('keeps the eclampsia preset anchored to preeclampsia', () => {
    const preset = PATIENT_PRESETS.find(({ id }) => id === 'pregnancy-severe-eclampsia')
    expect(preset).toBeDefined()
    const form = bundleToForm(preset!.bundle)

    expect(form.has_hypertension_after_week_20).toBe(true)
    expect(form.proteinuria_24h_mg).toBe('350')
    expect(form.has_proteinuria).toBe(true)
    expect(form.has_seizure).toBe(true)
  })

  it('loads a FHIR R4 pregnancy preset for every reachable Tree 12 branch', () => {
    const pregnancy = PATIENT_PRESETS.filter(({ category }) =>
      category === PREGNANCY || category === PREGNANCY_FOLLOW_UP)
    expect(pregnancy).toHaveLength(21)

    for (const preset of pregnancy) {
      expect(preset.bundle.id, preset.id).toMatch(
        /^bundle-(?:PG\d{3}(?:-fu1)?|PGF001-fu[0-3])$/,
      )
      expect(preset.bundle.timestamp, preset.id).toMatch(/T08:00:00\+07:00$/)
      const entries = preset.bundle.entry as Array<{
        fullUrl?: string
        resource: {
          resourceType: string
          id?: string
          gender?: string
        }
      }>
      expect(entries.length, preset.id).toBeGreaterThan(0)
      for (const entry of entries) {
        expect(entry.fullUrl, preset.id).toBe(
          `http://example.org/fhir/${entry.resource.resourceType}/${entry.resource.id}`,
        )
      }
      const patient = entries.find(({ resource }) => resource.resourceType === 'Patient')
      expect(patient?.resource.gender, preset.id).toBe('female')
    }
  })

  it.each([0, 1, 2, 3])(
    'keeps pregnancy episode follow-up %s as a complete longitudinal Bundle',
    (followUpNumber) => {
      const preset = PATIENT_PRESETS.find(
        ({ id }) => id === `pregnancy-episode-follow-up-${followUpNumber}`,
      )
      expect(preset).toBeDefined()
      const entries = preset!.bundle.entry as Array<{ resource: {
        resourceType: string
        extension?: Array<{ url: string; valueInteger?: number; valueString?: string }>
      } }>
      const encounters = entries.filter(({ resource }) => resource.resourceType === 'Encounter')
      const patient = entries.find(({ resource }) => resource.resourceType === 'Patient')!.resource

      expect(encounters).toHaveLength(followUpNumber + 1)
      expect(patient.extension).toContainEqual({
        url: 'http://cdss.local/fhir/StructureDefinition/input/pregnancy_episode_id',
        valueString: 'pregnancy-demo-001',
      })
      expect(patient.extension).toContainEqual({
        url: 'http://cdss.local/fhir/StructureDefinition/input/pregnancy_follow_up_number',
        valueInteger: followUpNumber,
      })
    },
  )
})
