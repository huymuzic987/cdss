import type { JsonObject, JsonValue } from '../../api/types'
import {
  PREGNANCY,
  PREGNANCY_FOLLOW_UP,
  type PatientPresetBundleDefinition,
} from './shared'

const PRESET_META_BASE = 'http://cdss.local/fhir/CodeSystem/preset'

const modules = import.meta.glob<JsonObject>(
  '../../../../data/fhir/pregnancy_presets/*.json',
  { eager: true, import: 'default' },
)

const catalog = Object.entries(modules)
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([, bundle]) => toPreset(bundle))

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
