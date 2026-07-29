import type { JsonObject, JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { EvidenceItem } from './types'
import { formatValue, humanize, localized, objectValue, stringValue } from './values'

export function parseEvidence(values: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): EvidenceItem[] {
  if (!Array.isArray(values)) return []
  return values.flatMap((entry, index) => {
    const item = objectValue(entry)
    if (!item) return []
    const value = formatValue(item.value, stringValue(item.unit))
    const label = localized(item, 'label', locale) || humanize(stringValue(item.id, `evidence_${index}`))
    return value ? [{ id: stringValue(item.id, `evidence-${index}`), label, value }] : []
  })
}

function nestedObject(root: JsonObject, key: string): JsonObject | null {
  return objectValue(root[key])
}

function localizedCode(code: string, labels: Record<string, [string, string]>, locale: ClinicalDecisionSupportLocale): string {
  const pair = labels[code]
  if (!pair) return humanize(code)
  return locale === 'vi' ? pair[1] : pair[0]
}

export function buildClinicalSummaryEvidence(
  presentation: JsonObject,
  context: JsonObject,
  hasMedicationOrder: boolean,
  locale: ClinicalDecisionSupportLocale,
): EvidenceItem[] {
  const items: EvidenceItem[] = []
  const diagnosis = nestedObject(context, 'diagnosis')
  const hypertensionClass = stringValue(diagnosis?.hypertension_class)
  if (hypertensionClass) {
    items.push({
      id: 'clinical-hypertension-stage',
      label: locale === 'vi' ? 'PhÃ¢n Ä‘á»™ tÄƒng huyáº¿t Ã¡p' : 'Hypertension stage',
      value: localizedCode(hypertensionClass, {
        NORMAL_BP: ['Normal blood pressure', 'Huyáº¿t Ã¡p bÃ¬nh thÆ°á»ng'],
        HIGH_NORMAL_BP: ['High-normal blood pressure', 'Huyáº¿t Ã¡p bÃ¬nh thÆ°á»ng cao'],
        GRADE_1_HYPERTENSION: ['Grade 1 hypertension', 'TÄƒng huyáº¿t Ã¡p Ä‘á»™ 1'],
        GRADE_2_HYPERTENSION: ['Grade 2 hypertension', 'TÄƒng huyáº¿t Ã¡p Ä‘á»™ 2'],
        ISOLATED_SYSTOLIC_HYPERTENSION: ['Isolated systolic hypertension', 'TÄƒng huyáº¿t Ã¡p tÃ¢m thu Ä‘Æ¡n Ä‘á»™c'],
        MASKED_HYPERTENSION: ['Masked hypertension', 'TÄƒng huyáº¿t Ã¡p áº©n giáº¥u'],
        HYPERTENSIVE_EMERGENCY: ['Hypertensive emergency', 'TÄƒng huyáº¿t Ã¡p cáº¥p cá»©u'],
      }, locale),
    })
  }

  const details = Array.isArray(presentation.clinical_details) ? presentation.clinical_details : []
  const conditions = Array.from(new Set(details.flatMap((entry) => {
    const detail = objectValue(entry)
    if (!detail || detail.category !== 'condition') return []
    const value = formatValue(detail.value)
    return value ? [value] : []
  })))
  if (conditions.length > 0) {
    items.push({
      id: 'clinical-comorbidities',
      label: locale === 'vi' ? 'Cháº©n Ä‘oÃ¡n vÃ  bá»‡nh Ä‘á»“ng máº¯c' : 'Diagnoses and comorbidities',
      value: conditions.join(', '),
    })
  }

  const risk = nestedObject(context, 'risk')
  const riskLevel = stringValue(risk?.level)
  if (riskLevel) {
    items.push({
      id: 'clinical-risk-level',
      label: locale === 'vi' ? 'Má»©c nguy cÆ¡ tim máº¡ch' : 'Cardiovascular risk level',
      value: localizedCode(riskLevel, {
        LOW: ['Low risk', 'Nguy cÆ¡ tháº¥p'],
        MODERATE: ['Moderate risk', 'Nguy cÆ¡ trung bÃ¬nh'],
        HIGH: ['High risk', 'Nguy cÆ¡ cao'],
        VERY_HIGH: ['Very high risk', 'Nguy cÆ¡ ráº¥t cao'],
      }, locale),
    })
  }

  if (hasMedicationOrder) {
    items.push({
      id: 'clinical-treatment-indication',
      label: locale === 'vi' ? 'Chá»‰ Ä‘á»‹nh Ä‘iá»u trá»‹' : 'Treatment indication',
      value: locale === 'vi'
        ? 'Má»©c huyáº¿t Ã¡p vÃ  há»“ sÆ¡ nguy cÆ¡ Ä‘Ã¡p á»©ng tiÃªu chÃ­ Ä‘iá»u trá»‹ báº±ng thuá»‘c.'
        : 'Blood pressure and the clinical risk profile meet criteria for pharmacologic treatment.',
    })
  }
  return items
}

export function mergeEvidence(...groups: EvidenceItem[][]): EvidenceItem[] {
  return Array.from(new Map(groups.flat().map((item) => [item.id, item])).values())
}

