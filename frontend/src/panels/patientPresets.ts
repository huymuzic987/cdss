import generatedBundles from './patientPresets/presets.generated.json'
import type { JsonObject } from '../api/types'
import type { PatientPreset } from './patientPresets/shared'

export type { PatientPreset } from './patientPresets/shared'

const PRESET_META_BASE = 'http://cdss.local/fhir/CodeSystem/preset'

export const PATIENT_PRESETS: PatientPreset[] = (generatedBundles as unknown as JsonObject[]).map((bundle) => {
  const meta = asObject(bundle.meta)
  const tags = Array.isArray(meta?.tag)
    ? meta.tag.map(asObject).filter((item): item is JsonObject => item !== null)
    : []
  const tag = (name: string) => tags.find(
    (item) => item.system === `${PRESET_META_BASE}/${name}`,
  )
  const identifier = asObject(bundle.identifier)
  const id = typeof identifier?.value === 'string' ? identifier.value : String(bundle.id)
  return {
    id,
    label: String(tag('label')?.display ?? id),
    category: String(tag('category')?.display ?? 'Generated Patient Presets'),
    description: String(tag('description')?.display ?? ''),
    bundle,
  }
})

function asObject(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as JsonObject
    : null
}
