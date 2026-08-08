import type { JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, RegimenMedicine } from './types'
import { localized, objectValue, stringValue } from './values'

const DOSE_LABELS: Record<string, { en: string, vi: string }> = {
  LOW_DOSE: { en: 'Low dose', vi: 'Liều thấp' }, LOW_TO_USUAL_DOSE: { en: 'Low to usual dose', vi: 'Liều thấp đến liều thông thường' },
  USUAL_DOSE: { en: 'Usual dose', vi: 'Liều thông thường' }, MAX_DOSE: { en: 'Maximum dose', vi: 'Liều tối đa' },
}
const GROUP_DETAILS = { A: 'RAS (ACE inhibitor / ARB / ARNI)', B: 'Beta-blocker', C: 'Calcium-channel blocker', D: 'Diuretic', MRA: 'Mineralocorticoid receptor antagonist', SGLT2i: 'SGLT2 inhibitor', GLP1RA: 'GLP-1 receptor agonist' } as const

export type ParsedComponent = FinalRegimenComponent & { generic: boolean, identity: string }

function canonicalGroup(code: string, name: string, subgroup = ''): FinalRegimenComponent['group'] {
  const value = `${code} ${name} ${subgroup}`.toLocaleLowerCase()
  if (/\bsglt2i?\b|sglt2[_ -]?inhibitor|dapagliflozin|empagliflozin/i.test(value)) return 'SGLT2i'
  if (/\bglp-?1\s*ra\b|glp1ra|glp1[_ -]?receptor[_ -]?agonist/i.test(value)) return 'GLP1RA'
  if (/\bmra\b|mineralocorticoid|spironolactone|eplerenone/i.test(value)) return 'MRA'
  if (/\bbeta.?block|labetalol|metoprolol|bisoprolol|esmolol|propranolol|atenolol/i.test(value) || code.toUpperCase() === 'B') return 'B'
  if (/\bcalcium.?channel|\bccb\b|dihydropyridine|amlodipine|nifedipine|nicardipine/i.test(value) || code.toUpperCase() === 'C') return 'C'
  if (/\bdiuretic|thiazide|furosemide|indapamide|chlorthalidone/i.test(value) || code.toUpperCase() === 'D') return 'D'
  if (/\bras\b|ace inhibitor|\bacei\b|\barb\b|\barni\b|ưcmc|ctta|enalapril|lisinopril|losartan|valsartan|sacubitril/i.test(value) || code.toUpperCase() === 'A') return 'A'
  return 'Others'
}

function genericGroupName(value: string, group: FinalRegimenComponent['group']): boolean {
  return [group, 'ras', 'ace inhibitor', 'arb', 'arni', 'beta blocker', 'beta-blocker', 'calcium channel blocker', 'calcium-channel blocker', 'ccb', 'diuretic', 'mra', 'mineralocorticoid receptor antagonist', 'sglt2i', 'sglt2 inhibitor', 'sglt2_inhibitor', 'glp1ra', 'glp-1ra', 'glp-1 receptor agonist', 'glp1_receptor_agonist'].includes(value.trim().toLocaleLowerCase())
}

export function parseComponent(value: JsonValue, locale: ClinicalDecisionSupportLocale, catalog: Record<string, RegimenMedicine[]>): ParsedComponent | null {
  const component = objectValue(value)
  if (!component) return null
  const code = stringValue(component.code)
  const name = stringValue(component.name, code)
  if (!name) return null
  const subgroup = stringValue(component.subgroup)
  const medicineId = stringValue(component.medicine_id)
  const medicine = medicineId ? Object.values(catalog).flat().find((item) => item.id === medicineId) : undefined
  const resolvedSubgroup = subgroup || medicine?.subgroup
  const group = medicine ? canonicalGroup(medicine.group, medicine.name, medicine.subgroup) : canonicalGroup(code, name, subgroup)
  const selectorKind = stringValue(component.selector_kind)
  const generic = selectorKind === 'class' || Boolean(code && !medicineId) || genericGroupName(name, group) || genericGroupName(code, group)
  const detail = generic && group !== 'Others' ? GROUP_DETAILS[group as keyof typeof GROUP_DETAILS] : group
  const rawStrategy = stringValue(component.dose_strategy)
  const dose = (generic ? undefined : stringValue(component.dose)) || DOSE_LABELS[rawStrategy || 'LOW_DOSE']?.[locale] || (locale === 'vi' ? 'Liều thấp' : 'Low dose')
  const identity = medicineId ? `medicine:${medicineId}` : group === 'Others' ? `Others:${name.toLocaleLowerCase()}` : group
  return {
    label: generic ? group : (medicine?.name || name), detail, group, dose,
    ...(resolvedSubgroup ? { subgroup: resolvedSubgroup } : {}),
    ...(medicineId ? { medicineId, selectorKind: 'medicine' as const } : {}),
    ...(selectorKind === 'group' || selectorKind === 'subgroup' ? { selectorKind } : {}),
    ...(rawStrategy === 'USUAL_DOSE' || rawStrategy === 'MAX_DOSE' ? { doseStrategy: rawStrategy } : {}), generic, identity,
  }
}

export function components(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale, catalog: Record<string, RegimenMedicine[]>): ParsedComponent[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => parseComponent(item, locale, catalog)).filter((item): item is ParsedComponent => item !== null)
}

export function alternativeComponents(value: JsonValue, locale: ClinicalDecisionSupportLocale, catalog: Record<string, RegimenMedicine[]>): ParsedComponent[] {
  return components(objectValue(value)?.components, locale, catalog)
}

export function localizedStep(value: JsonValue, locale: ClinicalDecisionSupportLocale): string {
  const step = objectValue(value)
  return step ? localized(step, 'text', locale) : ''
}
