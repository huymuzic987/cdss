import type { CatalogGroup, CatalogMedicine, EvaluationResponse, JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { explicitSubgroupMatches, subgroupMatches } from '../clinicalPresentation/regimenCatalog'
import type { ClinicalPresentation, FinalRegimenComponent, RegimenMedicine, RegimenSafetyFinding } from '../clinicalPresentation/types'
import { objectValue, stringValue } from '../clinicalPresentation/values'

export type RegimenSafetyWarningSeverity = 'ABSOLUTE' | 'RELATIVE' | 'INSUFFICIENT_DATA'

export interface RegimenSafetyWarning {
  severity: RegimenSafetyWarningSeverity
  text: string
}

interface SafetyFinding extends RegimenSafetyFinding {
  severity: RegimenSafetyWarningSeverity
}

const severityRank: Record<RegimenSafetyWarningSeverity, number> = {
  ABSOLUTE: 3,
  RELATIVE: 2,
  INSUFFICIENT_DATA: 1,
}

const targetForGroup: Record<string, string[]> = {
  A: ['ACE_INHIBITOR', 'ARB', 'DIRECT_RENIN_INHIBITOR'],
  B: ['BETA_BLOCKER'],
  C: ['DIHYDROPYRIDINE_CCB', 'NON_DIHYDROPYRIDINE_CCB', 'NICARDIPINE'],
  D: ['THIAZIDE_LIKE_DIURETIC'],
  MRA: ['MRA'],
  SGLT2i: ['SGLT2_INHIBITOR'],
  GLP1RA: ['GLP1RA'],
  Others: [],
}

function targetForMedicine(medicine: Pick<CatalogMedicine, 'name' | 'group_code' | 'subgroup'>): string {
  const name = medicine.name.toLocaleLowerCase()
  const subgroup = (medicine.subgroup ?? '').toLocaleLowerCase()
  const value = `${name} ${subgroup}`
  const group = medicine.group_code

  if (group === 'MRA' || /spironolactone|eplerenone|mra|mineralocorticoid/.test(value)) return 'MRA'
  if (group === 'SGLT2i' || /sglt2|sodium-glucose/.test(value)) return 'SGLT2_INHIBITOR'
  if (name === 'nicardipine') return 'NICARDIPINE'
  if (/non-dhp|non-dihydropyridine|diltiazem|verapamil/.test(value)) return 'NON_DIHYDROPYRIDINE_CCB'
  if (/dhp|dihydropyridine|amlodipine|felodipine|isradipine|lercanidipine|nifedipine|nitrendipine/.test(value)) return 'DIHYDROPYRIDINE_CCB'
  if (/ace inhibitor|acei|ace|enalapril|lisinopril|perindopril|captopril|ramipril/.test(value)) return 'ACE_INHIBITOR'
  if (/arb|angiotensin ii|losartan|valsartan|irbesartan|telmisartan|candesartan|olmesartan/.test(value)) return 'ARB'
  if (/renin|aliskiren/.test(value)) return 'DIRECT_RENIN_INHIBITOR'
  if (group === 'B' || /beta.?block|bisoprolol|atenolol|carvedilol|labetalol|metoprolol|propranolol/.test(value)) return 'BETA_BLOCKER'
  if (/thiazide|thiazide-like|hydrochlorothiazide|indapamide|chlorthalidone/.test(value)) return 'THIAZIDE_LIKE_DIURETIC'
  return targetForGroup[group]?.[0] ?? 'OTHER'
}

function profileFindings(value: JsonValue | undefined): SafetyFinding[] {
  const profile = objectValue(value)
  if (!profile) return []
  const findings = Array.isArray(profile.findings)
    ? profile.findings.flatMap((raw) => parseFinding(raw))
    : []
  const existingTargets = new Set(findings.map((finding) => finding.target).filter(Boolean))
  const blockedTargets = Array.isArray(profile.blocked_targets)
    ? profile.blocked_targets.filter((target): target is string => typeof target === 'string')
    : []
  const reviewTargets = Array.isArray(profile.review_targets)
    ? profile.review_targets.filter((target): target is string => typeof target === 'string')
    : []
  return [
    ...findings,
    ...blockedTargets.filter((target) => !existingTargets.has(target)).map((target) => ({ target, severity: 'ABSOLUTE' as const })),
    ...reviewTargets.filter((target) => !existingTargets.has(target) && !blockedTargets.includes(target)).map((target) => ({ target, severity: 'INSUFFICIENT_DATA' as const })),
  ]
}

function parseFinding(value: JsonValue): SafetyFinding[] {
  const raw = objectValue(value)
  if (!raw) return []
  const severity = stringValue(raw.severity)
  if (severity !== 'ABSOLUTE' && severity !== 'RELATIVE' && severity !== 'INSUFFICIENT_DATA') return []
  return [{
    severity,
    ...(stringValue(raw.target) ? { target: stringValue(raw.target) } : {}),
    ...(stringValue(raw.reason_code) ? { reasonCode: stringValue(raw.reason_code) } : {}),
    ...(stringValue(raw.reason_en) ? { reasonEn: stringValue(raw.reason_en) } : {}),
    ...(stringValue(raw.reason_vi) ? { reasonVi: stringValue(raw.reason_vi) } : {}),
    ...(stringValue(raw.drug_group) ? { drugGroup: stringValue(raw.drug_group) } : {}),
  }]
}

function findingsFromResult(result: EvaluationResponse): SafetyFinding[] {
  const values: JsonValue[] = [result.context.medication_safety, result.context.current_regimen_safety]
  for (const action of result.actions) {
    values.push(action.payload.medication_safety, action.payload.current_regimen_safety)
    const presentation = objectValue(action.payload.presentation)
    if (presentation) values.push(presentation.medication_safety, presentation.current_regimen_safety)
  }
  const findings = values.flatMap((value) => profileFindings(value))
  const unique = new Map<string, SafetyFinding>()
  for (const finding of findings) {
    const key = [finding.target, finding.severity, finding.reasonCode, finding.drugGroup].join('|')
    unique.set(key, finding)
  }
  return [...unique.values()]
}

function presentationMedicine(id: string, presentation: ClinicalPresentation): RegimenMedicine | undefined {
  return Object.values(presentation.regimenCatalog).flat().find((medicine) => medicine.id === id)
}

function medicineWarnings(
  medicine: CatalogMedicine,
  presentation: ClinicalPresentation,
  findings: SafetyFinding[],
  locale: ClinicalDecisionSupportLocale,
): RegimenSafetyWarning[] {
  const direct = presentationMedicine(medicine.drug_id, presentation)
  const directFindings: SafetyFinding[] = direct?.safetyFindings?.flatMap((finding) => {
    const severity = finding.severity
    return severity === 'ABSOLUTE' || severity === 'RELATIVE' || severity === 'INSUFFICIENT_DATA'
      ? [{ ...finding, severity }]
      : []
  }) ?? []
  if (direct?.safetyStatus === 'ABSOLUTE' || direct?.safetyStatus === 'RELATIVE' || direct?.safetyStatus === 'INSUFFICIENT_DATA') {
    directFindings.push({ severity: direct.safetyStatus, target: targetForMedicine(medicine) })
  }
  const target = targetForMedicine(medicine)
  const matchingFindings = findings.filter((finding) => {
    if (finding.target && finding.target !== target) return false
    if (finding.drugGroup && !subgroupMatches(medicine.subgroup ?? '', finding.drugGroup)) return false
    return true
  })
  return [...directFindings, ...matchingFindings]
    .sort((left, right) => severityRank[right.severity] - severityRank[left.severity])
    .map((finding) => ({ severity: finding.severity, text: warningText(finding, locale) }))
    .filter((warning, index, warnings) => warnings.findIndex((item) => item.severity === warning.severity && item.text === warning.text) === index)
}

function warningText(finding: SafetyFinding, locale: ClinicalDecisionSupportLocale): string {
  const label = finding.severity === 'ABSOLUTE'
    ? (locale === 'vi' ? 'Chống chỉ định tuyệt đối' : 'Absolute contraindication')
    : finding.severity === 'RELATIVE'
      ? (locale === 'vi' ? 'Chống chỉ định tương đối' : 'Relative contraindication')
      : (locale === 'vi' ? 'Chưa đạt kiểm tra an toàn' : 'Safety check incomplete')
  const reason = locale === 'vi' ? finding.reasonVi ?? finding.reasonEn : finding.reasonEn ?? finding.reasonVi
  return reason ? `${label}: ${reason}` : label
}

export function createRegimenSafetyWarningResolver(
  catalog: CatalogGroup[],
  presentation: ClinicalPresentation,
  result: EvaluationResponse,
  locale: ClinicalDecisionSupportLocale,
): (component: FinalRegimenComponent) => RegimenSafetyWarning[] {
  const findings = findingsFromResult(result)
  return (component) => {
    const group = catalog.find((item) => item.code === component.group)
    if (!group) return []
    const medicines = component.medicineId
      ? group.subgroups.flatMap((item) => item.medicines).filter((medicine) => medicine.drug_id === component.medicineId)
      : component.subgroup
        ? group.subgroups.filter((item) => (component.isCustom ? explicitSubgroupMatches : subgroupMatches)(item.name, component.subgroup ?? '')).flatMap((item) => item.medicines)
        : group.subgroups.flatMap((item) => item.medicines)
    return medicines.flatMap((medicine) => medicineWarnings(medicine, presentation, findings, locale))
      .sort((left, right) => severityRank[right.severity] - severityRank[left.severity])
      .filter((warning, index, warnings) => warnings.findIndex((item) => item.severity === warning.severity && item.text === warning.text) === index)
  }
}
