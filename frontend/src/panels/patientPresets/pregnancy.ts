import type { JsonObject, JsonValue } from '../../api/types'
import pregnancyBundles from './pregnancyBundles.generated.json'
import {
  PREGNANCY,
  PREGNANCY_FOLLOW_UP,
  type PatientPresetBundleDefinition,
} from './shared'

const PRESET_META_BASE = 'http://cdss.local/fhir/CodeSystem/preset'

// Keep the frontend catalog inside its own Docker build context. The canonical
// per-case FHIR files and this manifest are emitted together by
// scripts/generate_pregnancy_fhir_presets.py.
const catalog = (pregnancyBundles as unknown as JsonObject[]).map(toPreset)

export const pregnancyPresets: PatientPresetBundleDefinition[] =
  catalog.filter(({ category }) => category === PREGNANCY)

export const pregnancyFollowUpPresets: PatientPresetBundleDefinition[] =
  catalog.filter(({ category }) => category === PREGNANCY_FOLLOW_UP)

function toPreset(bundle: JsonObject): PatientPresetBundleDefinition {
  const id = stringProperty(bundle.identifier, 'value')
  const category = tagDisplay(bundle, 'category')
  const label = tagDisplay(bundle, 'label')
  const description = tagDisplay(bundle, 'description')
  if (!id || !category || !label || !description) {
    throw new Error(`FHIR pregnancy preset ${String(bundle.id)} has incomplete metadata`)
  }
  return { id, category, label, description, bundle }
}

function tagDisplay(bundle: JsonObject, suffix: string): string | undefined {
  const meta = asObject(bundle.meta)
  const tags = Array.isArray(meta?.tag) ? meta.tag : []
  for (const value of tags) {
    const tag = asObject(value)
    if (
      tag?.system === `${PRESET_META_BASE}/${suffix}`
      && typeof tag.display === 'string'
    ) {
      return tag.display
    }
  }
  return undefined
}

function stringProperty(value: JsonValue | undefined, key: string): string | undefined {
  const object = asObject(value)
  return typeof object?.[key] === 'string' ? object[key] : undefined
}

function asObject(value: JsonValue | undefined): JsonObject | undefined {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value
    : undefined
}
