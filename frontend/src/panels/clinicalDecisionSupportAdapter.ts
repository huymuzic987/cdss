import type { ExecutedAction, JsonObject, JsonValue } from '../api/types'
import type { ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'

export type OrderDecision = 'order' | 'do-not-order' | null

export interface RecommendedOrder {
  id: string
  name: string
  dose?: string
  classLabel?: string
  decision: OrderDecision
  orderType?: string
  sourceData?: JsonObject
  medicineIds?: string[]
}

export interface EvidenceItem {
  id: string
  label: string
  value: string
}

export interface ActionOption {
  id: string
  label: string
}

export interface AcknowledgementOption extends ActionOption {
  requiresText?: boolean
}

export interface ClinicalPresentation {
  alert: string
  evidence: EvidenceItem[]
  recommendation: string
  recommendationSecondary?: string
  recommendationStrength?: string
  evidenceLevel?: string
  orders: RecommendedOrder[]
  additionalActions: ActionOption[]
  acknowledgementOptions: AcknowledgementOption[]
  clinicalDetails: EvidenceItem[]
  guidelineReferences: GuidelineReference[]
  contractError?: string
}

export interface GuidelineReference {
  id: string
  title: string
  locator?: string
}

interface Medicine {
  drugId: string
  name: string
  dose: string
  classLabel: string
}

function objectValue(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonObject : null
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function localized(object: JsonObject, key: string, locale: ClinicalDecisionSupportLocale): string {
  return locale === 'vi'
    ? stringValue(object[`${key}_vi`], stringValue(object[key], stringValue(object[`${key}_en`])))
    : stringValue(object[`${key}_en`], stringValue(object[key], stringValue(object[`${key}_vi`])))
}

function humanize(key: string): string {
  const label = key.split('.').at(-1) ?? key
  return label.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
}

function formatValue(value: JsonValue, unit?: string): string | null {
  let result: string | null = null
  if (typeof value === 'string' || typeof value === 'number') result = String(value)
  else if (typeof value === 'boolean') result = value ? 'Yes' : 'No'
  else if (Array.isArray(value) && value.every((item) => ['string', 'number', 'boolean'].includes(typeof item))) {
    result = value.join(', ')
  }
  return result ? `${result}${unit ? ` ${unit}` : ''}` : null
}

function parseEvidence(values: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): EvidenceItem[] {
  if (!Array.isArray(values)) return []
  return values.flatMap((entry, index) => {
    const item = objectValue(entry)
    if (!item) return []
    const value = formatValue(item.value, stringValue(item.unit))
    const label = localized(item, 'label', locale) || humanize(stringValue(item.id, `evidence_${index}`))
    return value ? [{ id: stringValue(item.id, `evidence-${index}`), label, value }] : []
  })
}

function parseMedicine(value: JsonValue): Medicine | null {
  const medicine = objectValue(value)
  if (!medicine || medicine.available === false) return null
  const name = stringValue(medicine.name, stringValue(medicine.drug_name))
  if (!name) return null
  return {
    drugId: stringValue(medicine.drug_id, stringValue(medicine.id)),
    name,
    dose: stringValue(medicine.starting_dose, stringValue(medicine.dose_low, stringValue(medicine.dose))),
    classLabel: stringValue(medicine.class_label, stringValue(medicine.subgroup, stringValue(medicine.drug_class))),
  }
}

function parseStructuredOrders(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): RecommendedOrder[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((entry, index) => {
    const item = objectValue(entry)
    if (!item) return []
    const components = Array.isArray(item.components)
      ? item.components.map(parseMedicine).filter((medicine): medicine is Medicine => medicine !== null)
      : []
    const name = localized(item, 'name', locale) || components.map((component) => component.name).join(' + ')
    if (!name) return []
    const dose = stringValue(item.starting_dose, stringValue(item.dose))
      || components.map((component) => component.dose).filter(Boolean).join(' + ')
    const classLabel = localized(item, 'class_label', locale)
      || components.map((component) => component.classLabel).filter(Boolean).join(' + ')
    return [{
      id: stringValue(item.id, `order-${index}`), name, dose: dose || undefined,
      classLabel: classLabel || undefined, decision: null,
      orderType: stringValue(item.type, 'order'), sourceData: item,
      medicineIds: components.map((component) => component.drugId).filter(Boolean),
    }]
  })
}

function parseOptions(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): ActionOption[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((entry, index) => {
    if (typeof entry === 'string') return [{ id: entry, label: humanize(entry) }]
    const option = objectValue(entry)
    if (!option) return []
    const id = stringValue(option.id, `action-${index}`)
    return [{ id, label: localized(option, 'label', locale) || humanize(id) }]
  })
}

function findPresentation(actions: ExecutedAction[]): JsonObject | null {
  for (let index = actions.length - 1; index >= 0; index -= 1) {
    const payload = actions[index].payload
    const presentation = objectValue(payload.presentation)
    if (presentation) return presentation
  }
  return null
}

function localizedText(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): string {
  const text = objectValue(value)
  return text ? localized(text, 'text', locale) : ''
}

function codedLabel(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): string {
  const coded = objectValue(value)
  return coded ? localized(coded, 'label', locale) || stringValue(coded.code) : ''
}

function parseGuidelineReferences(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): GuidelineReference[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((entry, index) => {
    const reference = objectValue(entry)
    if (!reference) return []
    return [{
      id: stringValue(reference.id, `reference-${index}`),
      title: localized(reference, 'title', locale),
      locator: stringValue(reference.locator) || undefined,
    }]
  })
}

export function buildClinicalPresentation(
  actions: ExecutedAction[], _input: JsonObject, _context: JsonObject, locale: ClinicalDecisionSupportLocale,
): ClinicalPresentation {
  const presentation = findPresentation(actions)
  if (!presentation || presentation.schema_version !== '1.0') {
    return {
      alert: locale === 'vi' ? 'Dữ liệu trình bày quyết định lâm sàng không hợp lệ.' : 'Invalid clinical presentation contract.',
      evidence: [], recommendation: '', orders: [], additionalActions: [], acknowledgementOptions: [],
      clinicalDetails: [], guidelineReferences: [], contractError: 'missing_or_unsupported_presentation',
    }
  }
  const structuredOrders = parseStructuredOrders(presentation.recommended_orders, locale)
  const evidence = parseEvidence(presentation.trigger_evidence, locale)
  const lastAction = actions.at(-1)
  const recommendation = localizedText(presentation.recommendation, locale)
  const acknowledgement = parseOptions(presentation.acknowledgement_options, locale).map((option) => ({
    ...option,
    requiresText: objectValue((presentation.acknowledgement_options as JsonValue[] | undefined)?.find((entry) => objectValue(entry)?.id === option.id))?.requires_text === true,
  }))
  return {
    alert: localizedText(presentation.alert, locale),
    evidence,
    recommendation,
    recommendationSecondary: localizedText(presentation.recommendation, locale === 'vi' ? 'en' : 'vi') || (lastAction ? (locale === 'vi' ? lastAction.text_en : lastAction.text_vi) : undefined),
    recommendationStrength: codedLabel(presentation.evidence_strength, locale),
    evidenceLevel: codedLabel(presentation.evidence_level, locale),
    orders: Array.from(new Map(structuredOrders.map((order) => [order.id, order])).values()),
    additionalActions: parseOptions(presentation.additional_actions, locale),
    acknowledgementOptions: acknowledgement,
    clinicalDetails: parseEvidence(presentation.clinical_details, locale),
    guidelineReferences: parseGuidelineReferences(presentation.guideline_references, locale),
  }
}
