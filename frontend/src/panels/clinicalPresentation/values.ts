import type { JsonObject, JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

export function objectValue(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonObject : null
}

export function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

export function localized(object: JsonObject, key: string, locale: ClinicalDecisionSupportLocale): string {
  return locale === 'vi'
    ? stringValue(object[`${key}_vi`], stringValue(object[key], stringValue(object[`${key}_en`])))
    : stringValue(object[`${key}_en`], stringValue(object[key], stringValue(object[`${key}_vi`])))
}

export function humanize(key: string): string {
  const label = key.split('.').at(-1) ?? key
  return label.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
}

export function formatValue(value: JsonValue, unit?: string): string | null {
  let result: string | null = null
  if (typeof value === 'string' || typeof value === 'number') result = String(value)
  else if (typeof value === 'boolean') result = value ? 'Yes' : 'No'
  else if (Array.isArray(value) && value.every((item) => ['string', 'number', 'boolean'].includes(typeof item))) {
    result = value.join(', ')
  }
  return result ? `${result}${unit ? ` ${unit}` : ''}` : null
}
