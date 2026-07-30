import type { ExecutedAction, JsonObject, JsonValue } from '../api/types'
import type { ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'

export interface RecommendedOrder {
  id: string
  name: string
  dose?: string
  classLabel?: string
  orderType?: string
  sourceData?: JsonObject
  medicineIds?: string[]
  drugClasses?: RecommendedDrugClass[]
  strategyReferences: GuidelineReference[]
}

export interface RecommendedMedicine {
  id: string
  name: string
  dose: string
  route?: string
  subgroup?: string
}

export interface RecommendedDrugClass {
  code: string
  label: string
  doseLabel: string
  medicines: RecommendedMedicine[]
}

export interface GuidelineReference {
  id: string
  shortLabel: string
  nodeText: string
  treeName: string
  sourceTitle: string
  sectionPath: string
  locator?: string
  locatorDetail?: string
  note?: string
  printedPages: number[]
  pdfPages: number[]
}

export interface EvidenceItem {
  id: string
  label: string
  value: string
}

export interface ClinicalPresentation {
  alert: string
  alertSummary: string
  alertSeverity: 'warning' | 'critical'
  evidence: EvidenceItem[]
  recommendation: string
  recommendationStrength?: string
  evidenceLevel?: string
  orders: RecommendedOrder[]
  contractError?: string
}

const CONDITION_CODE_LABELS: Record<string, [string, string]> = {
  has_target_organ_damage: ['Target-organ damage', 'Tổn thương cơ quan đích'],
  has_mi_acs: ['Myocardial infarction / acute coronary syndrome', 'Nhồi máu cơ tim / hội chứng vành cấp'],
  has_acute_coronary_syndrome: ['Acute coronary syndrome', 'Hội chứng vành cấp'],
  has_cardiovascular_disease: ['Cardiovascular disease', 'Bệnh tim mạch'],
  has_coronary_artery_disease: ['Coronary artery disease', 'Bệnh mạch vành'],
  has_stroke: ['Stroke', 'Đột quỵ'],
  has_tia: ['Transient ischemic attack', 'Cơn thiếu máu não thoáng qua'],
  has_type_2_diabetes: ['Type 2 diabetes', 'Đái tháo đường type 2'],
  has_diabetes: ['Diabetes', 'Đái tháo đường'],
  has_heart_failure: ['Heart failure', 'Suy tim'],
  has_hfref: ['Heart failure with reduced ejection fraction', 'Suy tim phân suất tống máu giảm'],
  has_hfmref: ['Heart failure with mildly reduced ejection fraction', 'Suy tim phân suất tống máu giảm nhẹ'],
  has_hfpef: ['Heart failure with preserved ejection fraction', 'Suy tim phân suất tống máu bảo tồn'],
  has_ckd: ['Chronic kidney disease', 'Bệnh thận mạn'],
  has_ckd_stage_3_or_higher: ['Chronic kidney disease stage 3 or higher', 'Bệnh thận mạn giai đoạn 3 trở lên'],
  has_kidney_transplant: ['Kidney transplant', 'Ghép thận'],
  is_pregnant: ['Pregnancy', 'Mang thai'],
  is_postpartum: ['Postpartum', 'Sau sinh'],
  is_breastfeeding: ['Breastfeeding', 'Đang cho con bú'],
  has_hypertensive_crisis: ['Hypertensive crisis', 'Cơn tăng huyết áp'],
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

function buildClinicalSummaryEvidence(
  presentation: JsonObject,
  locale: ClinicalDecisionSupportLocale,
): EvidenceItem[] {
  const items: EvidenceItem[] = []
  const triggerEvidence = parseEvidence(presentation.trigger_evidence, locale)
  const systolic = triggerEvidence.find((item) => item.id === 'current-sbp')
  const diastolic = triggerEvidence.find((item) => item.id === 'current-dbp')
  if (systolic && diastolic) {
    const withoutUnit = (value: string) => value.replace(/\s*mmHg\s*$/i, '')
    items.push({
      id: 'clinical-current-bp',
      label: locale === 'vi' ? 'Huyết áp' : 'Blood Pressure',
      value: `${withoutUnit(systolic.value)}/${withoutUnit(diastolic.value)} mmHg`,
    })
  }

  const conditions = patientConditionLabels(presentation, locale)
  if (conditions.length > 0) {
    items.push({
      id: 'clinical-conditions',
      label: locale === 'vi' ? 'Bệnh lý' : 'Conditions',
      value: conditions.join(', '),
    })
  }
  return items
}

function patientConditionLabels(
  presentation: JsonObject,
  locale: ClinicalDecisionSupportLocale,
): string[] {
  const labels: string[] = []
  const alertSummary = objectValue(presentation.alert_summary)
  const findings = alertSummary?.findings
  if (Array.isArray(findings)) {
    for (const value of findings) {
      const finding = objectValue(value)
      if (!finding) continue
      const label = localized(finding, 'label', locale)
      if (label) labels.push(label)
    }
  }
  const details = presentation.clinical_details
  if (Array.isArray(details)) {
    for (const value of details) {
      const detail = objectValue(value)
      if (
        !detail
        || stringValue(detail.category) !== 'condition'
        || detail.active === false
      ) continue
      const label = formatValue(detail.value)
      if (label) labels.push(physicianConditionLabel(label, locale))
    }
  }
  return Array.from(new Map(
    labels.map((label) => [label.trim().toLocaleLowerCase(), label.trim()]),
  ).values())
}

function physicianConditionLabel(
  value: string,
  locale: ClinicalDecisionSupportLocale,
): string {
  const normalized = value.trim().toLowerCase()
  const mapped = CONDITION_CODE_LABELS[normalized]
  if (mapped) return locale === 'vi' ? mapped[1] : mapped[0]
  if (!/^(?:has|is)_/.test(normalized)) return value.trim()
  const readable = normalized
    .replace(/^(?:has|is)_/, '')
    .replaceAll('_', ' ')
    .replace(/\s+/g, ' ')
  return readable ? readable.charAt(0).toUpperCase() + readable.slice(1) : ''
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
    const drugClasses = parseDrugClasses(item.drug_classes, locale)
    return [{
      id: stringValue(item.id, `order-${index}`), name, dose: dose || undefined,
      classLabel: classLabel || undefined,
      orderType: stringValue(item.type, 'order'), sourceData: item,
      medicineIds: components.map((component) => component.drugId).filter(Boolean),
      drugClasses: drugClasses.length > 0 ? drugClasses : undefined,
      strategyReferences: parseGuidelineReferences(item.strategy_references, locale),
    }]
  })
}

function parseDrugClasses(
  value: JsonValue | undefined,
  locale: ClinicalDecisionSupportLocale,
): RecommendedDrugClass[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((entry, classIndex) => {
    const drugClass = objectValue(entry)
    if (!drugClass) return []
    const code = stringValue(drugClass.code, String(classIndex + 1))
    const medicines = Array.isArray(drugClass.medicines)
      ? drugClass.medicines.flatMap((rawMedicine, medicineIndex) => {
          const medicine = objectValue(rawMedicine)
          if (!medicine) return []
          const name = stringValue(medicine.name)
          const dose = stringValue(medicine.dose)
          if (!name || !dose) return []
          return [{
            id: stringValue(medicine.id, `${code}-medicine-${medicineIndex}`),
            name,
            dose,
            route: stringValue(medicine.route) || undefined,
            subgroup: stringValue(medicine.subgroup) || undefined,
          }]
        })
      : []
    return [{
      code,
      label: localized(drugClass, 'label', locale) || `${locale === 'vi' ? 'Nhóm thuốc' : 'Drug Class'} ${code}`,
      doseLabel: localized(drugClass, 'dose_label', locale),
      medicines,
    }]
  })
}

function numberList(value: JsonValue | undefined): number[] {
  return Array.isArray(value)
    ? value.filter((item): item is number => typeof item === 'number')
    : []
}

function formatSectionPath(value: JsonValue | undefined): string {
  if (!Array.isArray(value)) return ''
  return value.flatMap((entry) => {
    const section = objectValue(entry)
    if (!section) return []
    const number = stringValue(section.number)
    const title = stringValue(section.title)
    const text = [number, title].filter(Boolean).join(' ')
    return text ? [text] : []
  }).join(' > ')
}

function shortReferenceLabel(locator: string, sectionPath: string, locale: ClinicalDecisionSupportLocale): string {
  const locatorMatch = locator.match(/\b(?:Bảng|Table)\s+\d+(?:\.\d+)?/iu)
    ?? locator.match(/\b(?:Mục|Section)\s+\d+(?:\.\d+)*/iu)
  if (locatorMatch) return locatorMatch[0]
  const sectionNumber = sectionPath.match(/^\d+(?:\.\d+)*/)
  if (sectionNumber) return `${locale === 'vi' ? 'Mục' : 'Section'} ${sectionNumber[0]}`
  return locator || (locale === 'vi' ? 'Nguồn' : 'Source')
}

function parseGuidelineReferences(
  value: JsonValue | undefined,
  locale: ClinicalDecisionSupportLocale,
): GuidelineReference[] {
  if (!Array.isArray(value)) return []
  const references = value.flatMap((entry, index) => {
    const reference = objectValue(entry)
    if (!reference) return []
    const locator = stringValue(reference.locator)
    const sectionPath = formatSectionPath(reference.section_path)
    return [{
      id: stringValue(reference.id, `strategy-reference-${index}`),
      shortLabel: shortReferenceLabel(locator, sectionPath, locale),
      nodeText: localized(reference, 'node_text', locale),
      treeName: localized(reference, 'tree_name', locale),
      sourceTitle: localized(reference, 'title', locale),
      sectionPath,
      locator: locator || undefined,
      locatorDetail: stringValue(reference.locator_detail) || undefined,
      note: stringValue(reference.note) || undefined,
      printedPages: numberList(reference.printed_page_numbers),
      pdfPages: numberList(reference.pdf_page_numbers),
    }]
  })
  return Array.from(new Map(
    references.map((reference) => [reference.id, reference]),
  ).values())
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

export function buildClinicalPresentation(
  actions: ExecutedAction[], _input: JsonObject, _context: JsonObject, locale: ClinicalDecisionSupportLocale,
): ClinicalPresentation {
  const presentation = findPresentation(actions)
  if (!presentation || presentation.schema_version !== '1.0') {
    return {
      alert: locale === 'vi' ? 'Dữ liệu trình bày quyết định lâm sàng không hợp lệ.' : 'Invalid clinical presentation contract.',
      alertSummary: '',
      alertSeverity: 'warning',
      evidence: [], recommendation: '', orders: [],
      contractError: 'missing_or_unsupported_presentation',
    }
  }
  const structuredOrders = parseStructuredOrders(presentation.recommended_orders, locale)
  const evidence = buildClinicalSummaryEvidence(presentation, locale)
  const alertSummaryPayload = objectValue(presentation.alert_summary)
  const crisisClassification = objectValue(alertSummaryPayload?.hypertensive_crisis_classification)
  const alertSeverity = stringValue(crisisClassification?.code) === 'EMERGENCY_HYPERTENSION'
    ? 'critical'
    : 'warning'
  const terminalAction = actions.findLast(
    (action) => action.node_type === 'ACTION' || action.node_type === 'END',
  )
  const terminalRecommendation = terminalAction
    ? terminalAction.text_en || terminalAction.text_vi
    : ''
  const recommendation = terminalRecommendation
    || localizedText(presentation.recommendation, 'en')
  return {
    alert: localizedText(presentation.alert, locale),
    alertSummary: localizedText(presentation.alert_summary, locale),
    alertSeverity,
    evidence,
    recommendation,
    recommendationStrength: codedLabel(presentation.evidence_strength, locale),
    evidenceLevel: codedLabel(presentation.evidence_level, locale),
    orders: Array.from(new Map(structuredOrders.map((order) => [order.id, order])).values()),
  }
}
