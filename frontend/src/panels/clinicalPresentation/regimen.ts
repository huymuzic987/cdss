import type { JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, FinalRegimenOption, RegimenMedicine, RegimenStep } from './types'
import { componentLabel, isStopped } from './regimenLabels'
import { parseRegimenCatalog } from './regimenCatalog'
import { uniqueRegimenOptions } from './regimenOptions'
import { localized, objectValue, stringValue } from './values'

const DOSE_LABELS: Record<string, { en: string, vi: string }> = {
  LOW_DOSE: { en: 'Low dose', vi: 'Liều thấp' },
  LOW_TO_USUAL_DOSE: { en: 'Low to usual dose', vi: 'Liều thấp đến liều thông thường' },
  USUAL_DOSE: { en: 'Usual dose', vi: 'Liều thông thường' },
  MAX_DOSE: { en: 'Maximum dose', vi: 'Liều tối đa' },
}

const GROUP_DETAILS = {
  A: 'RAS (ACE inhibitor / ARB / ARNI)',
  B: 'Beta-blocker',
  C: 'Calcium-channel blocker',
  D: 'Diuretic',
  MRA: 'Mineralocorticoid receptor antagonist',
  SGLT2i: 'SGLT2 inhibitor',
  GLP1RA: 'GLP-1 receptor agonist',
} as const

type ParsedComponent = FinalRegimenComponent & { generic: boolean, identity: string }

function canonicalGroup(code: string, name: string, subgroup = ''): FinalRegimenComponent['group'] {
  const value = `${code} ${name} ${subgroup}`.toLocaleLowerCase()
  if (/(\bsglt2i?\b|sglt2[_ -]?inhibitor|dapagliflozin|empagliflozin)/i.test(value)) return 'SGLT2i'
  if (/(\bglp-?1\s*ra\b|glp1ra|glp1[_ -]?receptor[_ -]?agonist)/i.test(value)) return 'GLP1RA'
  if (/(\bmra\b|mineralocorticoid|spironolactone|eplerenone)/i.test(value)) return 'MRA'
  if (/(\bbeta.?block|labetalol|metoprolol|bisoprolol|esmolol|propranolol|atenolol)/i.test(value) || code.toUpperCase() === 'B') return 'B'
  if (/(\bcalcium.?channel|\bccb\b|dihydropyridine|amlodipine|nifedipine|nicardipine)/i.test(value) || code.toUpperCase() === 'C') return 'C'
  if (/(\bdiuretic|thiazide|furosemide|indapamide|chlorthalidone)/i.test(value) || code.toUpperCase() === 'D') return 'D'
  if (/(\bras\b|ace inhibitor|\bacei\b|\barb\b|\barni\b|ưcmc|ctta|enalapril|lisinopril|losartan|valsartan|sacubitril)/i.test(value) || code.toUpperCase() === 'A') return 'A'
  return 'Others'
}

function genericGroupName(value: string, group: FinalRegimenComponent['group']): boolean {
  const normalized = value.trim().toLocaleLowerCase()
  if (normalized === group.toLocaleLowerCase()) return true
  return [
    'ras', 'ace inhibitor', 'arb', 'arni', 'beta blocker', 'beta-blocker',
    'calcium channel blocker', 'calcium-channel blocker', 'ccb', 'diuretic',
    'mra', 'mineralocorticoid receptor antagonist',
    'sglt2i', 'sglt2 inhibitor', 'sglt2_inhibitor',
    'glp1ra', 'glp-1ra', 'glp-1 receptor agonist', 'glp1_receptor_agonist',
  ].includes(normalized)
}

function parseComponent(
  value: JsonValue,
  locale: ClinicalDecisionSupportLocale,
): ParsedComponent | null {
  const component = objectValue(value)
  if (!component) return null
  const code = stringValue(component.code)
  const name = stringValue(component.name, code)
  if (!name) return null
  const subgroup = stringValue(component.subgroup)
  const group = canonicalGroup(code, name, subgroup)
  const selectorKind = stringValue(component.selector_kind)
  const classComponent = selectorKind === 'class' || Boolean(code && !component.medicine_id)
  const generic = classComponent
    || genericGroupName(name, group)
    || genericGroupName(code, group)
  const detail = generic && group !== 'Others'
    ? GROUP_DETAILS[group as keyof typeof GROUP_DETAILS]
    : group
  const label = generic ? group : name
  const identity = group === 'Others' ? `Others:${name.toLocaleLowerCase()}` : group
  const strategy = stringValue(component.dose_strategy, 'LOW_DOSE')
  const dose = (generic ? undefined : stringValue(component.dose))
    || DOSE_LABELS[strategy]?.[locale]
    || (locale === 'vi' ? 'Liều thấp' : 'Low dose')
  return {
    label,
    detail,
    group,
    dose,
    ...(subgroup ? { subgroup } : {}),
    generic,
    identity,
  }
}

function components(
  value: JsonValue | undefined,
  locale: ClinicalDecisionSupportLocale,
  _catalog: Record<string, RegimenMedicine[]>,
): ParsedComponent[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => parseComponent(item, locale))
    .filter((item): item is ParsedComponent => item !== null)
}

function alternativeComponents(
  value: JsonValue,
  locale: ClinicalDecisionSupportLocale,
  catalog: Record<string, RegimenMedicine[]>,
): ParsedComponent[] {
  return components(objectValue(value)?.components, locale, catalog)
}

function alternativeLabel(
  value: JsonValue,
  locale: ClinicalDecisionSupportLocale,
  catalog: Record<string, RegimenMedicine[]>,
): string {
  return alternativeComponents(value, locale, catalog)
    .map((item) => componentLabel(item, locale)).join(' + ')
}

function mergeSubgroups(first: string | undefined, second: string | undefined): string | undefined {
  const values = [first, second]
    .flatMap((value) => value?.split('/').map((part) => part.trim()) ?? [])
    .filter(Boolean)
  return values.length > 0 ? [...new Set(values)].join(' / ') : undefined
}

function deduplicate(items: ParsedComponent[]): FinalRegimenComponent[] {
  const selected = new Map<string, ParsedComponent>()
  for (const item of items) {
    const previous = selected.get(item.identity)
    if (!previous || (previous.generic && !item.generic)) {
      selected.set(item.identity, item)
    } else if (!previous.subgroup && item.subgroup) {
      selected.set(item.identity, item)
    } else if (previous.subgroup && item.subgroup) {
      selected.set(item.identity, {
        ...previous,
        subgroup: mergeSubgroups(previous.subgroup, item.subgroup),
      })
    }
  }
  return [...selected.values()].map(({ generic: _generic, identity: _identity, ...item }) => item)
}

export function parseRegimenPlan(
  value: JsonValue | undefined,
  locale: ClinicalDecisionSupportLocale,
  catalog: Record<string, RegimenMedicine[]> = {},
): RegimenStep[] {
  const plan = objectValue(value)
  if (!plan || plan.schema_version !== '1.0' || !Array.isArray(plan.steps)) return []
  const sourceCatalog = Object.keys(catalog).length > 0 ? catalog : parseRegimenCatalog(value)
  return plan.steps.flatMap((raw, index) => {
    const step = objectValue(raw)
    if (!step) return []
    const operation = stringValue(step.keyword)
    const direct = components(step.components, locale, sourceCatalog)
    const alternatives = Array.isArray(step.alternatives)
      ? step.alternatives.map((item) => alternativeLabel(item, locale, sourceCatalog)).filter(Boolean)
      : []
    const stepComponentLabel = direct.map((item) => componentLabel(item, locale)).join(' + ')
      || alternatives.join(locale === 'vi' ? ' hoặc ' : ' or ')
    const doses = Array.from(new Set(direct.map((item) => item.dose)))
    if (doses.length === 0 && Array.isArray(step.alternatives)) {
      for (const rawAlternative of step.alternatives) {
        for (const item of alternativeComponents(rawAlternative, locale, sourceCatalog)) {
          if (!doses.includes(item.dose)) doses.push(item.dose)
        }
      }
    }
    return [{
      id: stringValue(step.id, `regimen-step-${index}`),
      treeKey: stringValue(step.tree_key),
      nodeKey: stringValue(step.node_key),
      operation,
      instruction: localized(step, 'text', locale) || stepComponentLabel,
      componentLabel: stepComponentLabel,
      doseLabel: doses.join(' / '),
    }]
  })
}

export function parseFinalRegimenOptions(
  value: JsonValue | undefined,
  locale: ClinicalDecisionSupportLocale,
  catalog: Record<string, RegimenMedicine[]> = {},
): FinalRegimenOption[] {
  const effective = objectValue(objectValue(value)?.effective_regimen)
  if (!effective) return []
  const sourceCatalog = Object.keys(catalog).length > 0 ? catalog : parseRegimenCatalog(value)

  const bases = Array.isArray(effective.base_options)
    ? effective.base_options.map((item) => alternativeComponents(item, locale, sourceCatalog)).filter((item) => item.length > 0)
    : []
  const additions = components(effective.additions, locale, sourceCatalog)
  const stopped = components(effective.stopped_components, locale, sourceCatalog)
  let candidates = bases.length > 0 ? bases : additions.length > 0 ? [[]] : []
  let fallbackAdditions = additions
  if (candidates.length === 0) {
    const rawSteps = objectValue(value)?.steps
    const steps = Array.isArray(rawSteps) ? rawSteps : []
    const lastMaterialStep = [...steps].reverse().map((item) => objectValue(item))
      .find((step) => step && !['REMOVE', 'STOP', 'AVOID'].includes(stringValue(step.keyword).toLocaleUpperCase()) && (components(step.components, locale, sourceCatalog).length > 0 || (Array.isArray(step.alternatives) && step.alternatives.length > 0)))
    const alternatives = Array.isArray(lastMaterialStep?.alternatives)
      ? lastMaterialStep.alternatives.map((item) => alternativeComponents(item, locale, sourceCatalog))
        .filter((item) => item.length > 0)
      : []
    const direct = components(lastMaterialStep?.components, locale, sourceCatalog)
    candidates = alternatives.length > 0 ? alternatives : direct.length > 0 ? [[]] : []
    fallbackAdditions = alternatives.length > 0 ? [] : direct
  }

  const options = candidates.map((base, index) => ({
    id: `regimen-option-${index + 1}`,
    components: deduplicate([...base, ...fallbackAdditions])
      .filter((item) => !stopped.some((stop) => isStopped(item, stop))),
  })).filter((option) => option.components.length > 0)
  return uniqueRegimenOptions(options)
}

export { parseRegimenCatalog } from './regimenCatalog'
