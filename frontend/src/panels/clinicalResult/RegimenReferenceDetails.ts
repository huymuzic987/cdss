import type { ExecutedReference, JsonValue } from '../../api/types'

export function uniqueReferenceDetails(references: ExecutedReference[]): string[] {
  return Array.from(new Set(references.flatMap((reference) => {
    const section = sectionLabel(reference.section_path)
    const locator = reference.locator?.trim()
    return [section, locator].filter((value): value is string => Boolean(value))
  })))
}

function sectionLabel(value: JsonValue): string {
  if (!Array.isArray(value)) return ''
  return value.flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return []
    const number = typeof item.number === 'string' ? item.number.trim() : ''
    const title = typeof item.title === 'string' ? item.title.trim() : ''
    if (!number && !title) return []
    return [`Mục ${number}${number && title ? '. ' : ''}${title}`]
  }).join(' · ')
}
