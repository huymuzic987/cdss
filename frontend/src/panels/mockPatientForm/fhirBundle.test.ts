import { describe, expect, it } from 'vitest'
import { PATIENT_PRESETS } from '../patientPresets'
import {
  FOLLOW_UP,
  PREGNANCY,
  PREGNANCY_FOLLOW_UP,
} from '../patientPresets/shared'
import { bundleToForm, formToPayload } from './payload'
import { validatePatientForm } from './validation'

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

  it('keeps aspirin prophylaxis normotensive and high-risk', () => {
    const preset = PATIENT_PRESETS.find(
      ({ id }) => id === 'pregnancy-high-preeclampsia-risk-aspirin',
    )
    expect(preset).toBeDefined()
    const form = bundleToForm(preset!.bundle)

    expect(form.current_clinic_sbp).toBe('130')
    expect(form.current_clinic_dbp).toBe('80')
    expect(form.has_high_preeclampsia_risk).toBe(true)
    expect(form.has_hypertension_after_week_20).toBe(false)
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
        /^bundle-(?:PG\d{3}|PGF001-fu[0-3])$/,
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
