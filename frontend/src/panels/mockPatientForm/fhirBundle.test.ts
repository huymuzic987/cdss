import { describe, expect, it } from 'vitest'
import { PATIENT_PRESETS } from '../patientPresets'
import { bundleToForm, formToPayload } from './payload'

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

  it('keeps the eclampsia preset anchored to preeclampsia', () => {
    const preset = PATIENT_PRESETS.find(({ id }) => id === 'pregnancy-severe-eclampsia')
    expect(preset).toBeDefined()
    const form = bundleToForm(preset!.bundle)

    expect(form.has_hypertension_after_week_20).toBe(true)
    expect(form.proteinuria_24h_mg).toBe('350')
    expect(form.has_severe_headache).toBe(true)
    expect(form.has_visual_disturbance).toBe(true)
  })
})
