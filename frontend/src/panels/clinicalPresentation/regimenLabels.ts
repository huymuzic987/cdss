import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent } from './types'

type ParsedComponent = FinalRegimenComponent & { generic?: boolean }

export function regimenSubgroupLabel(
  subgroup: string | undefined,
  locale: ClinicalDecisionSupportLocale = 'en',
): string | undefined {
  void locale
  return subgroup
}

export function componentLabel(
  item: ParsedComponent,
  locale: ClinicalDecisionSupportLocale = 'en',
): string {
  const base = item.generic || item.detail === item.label
    ? item.label
    : `${item.label} (${item.detail})`
  const subgroup = regimenSubgroupLabel(item.subgroup, locale)
  return subgroup ? `${base} (${subgroup})` : base
}

export function isStopped(item: ParsedComponent, stop: ParsedComponent): boolean {
  if (item.group !== stop.group) return false
  if (stop.subgroup) {
    return item.subgroup?.toLocaleLowerCase() === stop.subgroup.toLocaleLowerCase()
  }
  return stop.label.toLocaleUpperCase() === item.label.toLocaleUpperCase()
    || (stop.generic === true && item.generic === true)
}
