import type { JsonValue } from '../../api/types'
import type { RegimenMedicine } from './types'
import { objectValue, stringValue } from './values'

const TOKEN_PATTERN = /[\p{L}\p{N}]+(?:-[\p{L}\p{N}]+)*/gu

export function parseRegimenCatalog(
  value: JsonValue | undefined,
): Record<string, RegimenMedicine[]> {
  const plan = objectValue(value)
  const rawCatalog = plan?.catalog_by_class
  const classEntries = rawCatalog && typeof rawCatalog === 'object' && !Array.isArray(rawCatalog)
    ? Object.entries(rawCatalog)
    : []
  const parsed = Object.fromEntries(classEntries.map(([group, rawItems]) => {
    if (!Array.isArray(rawItems)) return [group, []]
    return [group, parseCatalogMedicines(rawItems, group)]
  }))
  if (Array.isArray(plan?.catalog)) parsed.__all__ = parseCatalogMedicines(plan.catalog, 'Others')
  return parsed
}

export function recognizeRegimenSubgroup(
  value: string,
  group: string,
  catalog: Record<string, RegimenMedicine[]>,
): string | undefined {
  const allMedicines = catalog.__all__ ?? Object.values(catalog).flat()
  const groupMedicines = catalog[group] && catalog[group].length > 0
    ? catalog[group]
    : allMedicines.filter((medicine) => medicine.group.toLocaleLowerCase() === group.toLocaleLowerCase())
  const subgroups = Array.from(new Map(
    groupMedicines
      .map((medicine) => medicine.subgroup)
      .filter(Boolean)
      .map((subgroup) => [subgroup.toLocaleLowerCase(), subgroup]),
  ).values())
  const matches = subgroups.filter((subgroup) => mentions(value, subgroup))
  return matches.length > 0 ? matches.join(' / ') : undefined
}

export function subgroupMatches(actual: string, expected: string): boolean {
  const actualTokens = tokens(actual)
  return expected.split('/').some((part) => (
    tokens(part.trim()).every((term) => termMatches(term, actualTokens))
  ))
}

function mentions(text: string, subgroup: string): boolean {
  const textTokens = tokens(text)
  return tokens(subgroup).some((term) => termMatches(term, textTokens))
}

function termMatches(term: string, textTokens: string[]): boolean {
  if (textTokens.includes(term)) return true
  if (term.includes('-') || term.length < 3) return false
  return textTokens.some((word) => (
    !word.includes('-')
    && word.length > term.length
    && isSubsequence(term, word)
  ))
}

function tokens(value: string): string[] {
  return value.toLocaleLowerCase().normalize('NFKD').replace(/\p{M}/gu, '').match(TOKEN_PATTERN) ?? []
}

function isSubsequence(short: string, long: string): boolean {
  let position = 0
  for (const character of long) {
    if (character === short[position]) position += 1
  }
  return position === short.length
}

function parseCatalogMedicines(rawItems: JsonValue[], fallbackGroup: string): RegimenMedicine[] {
  return rawItems.flatMap((raw) => {
    const item = objectValue(raw)
    if (!item) return []
    return [{
      id: stringValue(item.drug_id),
      name: stringValue(item.name),
      group: stringValue(item.drug_class, fallbackGroup),
      subgroup: stringValue(item.subgroup),
      route: stringValue(item.route),
      doseLow: stringValue(item.dose_low),
      doseUsual: stringValue(item.dose_usual),
      doseMax: stringValue(item.dose_max),
      snomedCode: stringValue(item.snomed_code),
      safetyStatus: stringValue(item.safety_status) || undefined,
    }]
  })
}
