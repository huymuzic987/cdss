import type { JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, FinalRegimenOption, RegimenMedicine, RegimenStep } from './types'
import { isStopped } from './regimenLabels'
import { parseRegimenCatalog } from './regimenCatalog'
import { uniqueRegimenOptions } from './regimenOptions'
import { alternativeComponents, components, localizedStep, type ParsedComponent } from './regimenComponentParser'
import { objectValue, stringValue } from './values'

function mergeSubgroups(first: string | undefined, second: string | undefined): string | undefined {
  const values = [first, second].flatMap((value) => value?.split('/').map((part) => part.trim()) ?? []).filter(Boolean)
  return values.length > 0 ? [...new Set(values)].join(' / ') : undefined
}

function deduplicate(items: ParsedComponent[]): FinalRegimenComponent[] {
  const selected = new Map<string, ParsedComponent>()
  for (const item of items) {
    const previous = selected.get(item.identity)
    if (!previous || (previous.generic && !item.generic)) selected.set(item.identity, item)
    else if (!previous.subgroup && item.subgroup) selected.set(item.identity, item)
    else if (previous.subgroup && item.subgroup) selected.set(item.identity, { ...previous, subgroup: mergeSubgroups(previous.subgroup, item.subgroup) })
  }
  return [...selected.values()].map(({ generic: _generic, identity: _identity, ...item }) => item)
}

export function parseRegimenPlan(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale, catalog: Record<string, RegimenMedicine[]> = {}): RegimenStep[] {
  const plan = objectValue(value)
  if (!plan || plan.schema_version !== '1.0' || !Array.isArray(plan.steps)) return []
  const sourceCatalog = Object.keys(catalog).length > 0 ? catalog : parseRegimenCatalog(value)
  return plan.steps.flatMap((raw, index) => {
    const step = objectValue(raw)
    if (!step) return []
    const operation = stringValue(step.keyword)
    const direct = components(step.components, locale, sourceCatalog)
    const alternatives = Array.isArray(step.alternatives) ? step.alternatives.map((item) => alternativeComponents(item, locale, sourceCatalog).map((component) => component.label).join(' + ')).filter(Boolean) : []
    const componentLabel = direct.map((item) => item.label).join(' + ') || alternatives.join(locale === 'vi' ? ' hoặc ' : ' or ')
    const doses = Array.from(new Set(direct.map((item) => item.dose)))
    if (doses.length === 0 && Array.isArray(step.alternatives)) {
      step.alternatives.forEach((item) => alternativeComponents(item, locale, sourceCatalog).forEach((component) => {
        if (!doses.includes(component.dose)) doses.push(component.dose)
      }))
    }
    return [{ id: stringValue(step.id, `regimen-step-${index}`), treeKey: stringValue(step.tree_key), nodeKey: stringValue(step.node_key), operation, instruction: localizedStep(step, locale) || componentLabel, componentLabel, doseLabel: doses.join(' / ') }]
  })
}

export function parseFinalRegimenOptions(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale, catalog: Record<string, RegimenMedicine[]> = {}): FinalRegimenOption[] {
  const effective = objectValue(objectValue(value)?.effective_regimen)
  if (!effective) return []
  const sourceCatalog = Object.keys(catalog).length > 0 ? catalog : parseRegimenCatalog(value)
  const bases = Array.isArray(effective.base_options) ? effective.base_options.map((item) => alternativeComponents(item, locale, sourceCatalog)).filter((item) => item.length > 0) : []
  const additions = components(effective.additions, locale, sourceCatalog)
  const stopped = components(effective.stopped_components, locale, sourceCatalog)
  let candidates = bases.length > 0 ? bases : additions.length > 0 ? [[]] : []
  let fallbackAdditions = additions
  if (candidates.length === 0) {
    const rawSteps = objectValue(value)?.steps
    const steps = Array.isArray(rawSteps) ? rawSteps : []
    const last = [...steps].reverse().map((item) => objectValue(item)).find((step) => step && !['REMOVE', 'STOP', 'AVOID'].includes(stringValue(step.keyword).toLocaleUpperCase()) && (components(step.components, locale, sourceCatalog).length > 0 || (Array.isArray(step.alternatives) && step.alternatives.length > 0)))
    const alternatives = Array.isArray(last?.alternatives) ? last.alternatives.map((item) => alternativeComponents(item, locale, sourceCatalog)).filter((item) => item.length > 0) : []
    const direct = components(last?.components, locale, sourceCatalog)
    candidates = alternatives.length > 0 ? alternatives : direct.length > 0 ? [[]] : []
    fallbackAdditions = alternatives.length > 0 ? [] : direct
  }
  return uniqueRegimenOptions(candidates.map((base, index) => ({ id: `regimen-option-${index + 1}`, components: deduplicate([...base, ...fallbackAdditions]).filter((item) => !stopped.some((stop) => isStopped(item, stop))) })).filter((option) => option.components.length > 0))
}

export { parseRegimenCatalog } from './regimenCatalog'
