import type { FinalRegimenComponent, RegimenMedicine } from '../clinicalPresentation/types'
import { subgroupMatches } from '../clinicalPresentation/regimenCatalog'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { drugClassDisplay } from './drugClassLabels'

export const GROUP_NAMES = {
  A: 'RAS: ACE inhibitor / ARB / ARNI',
  B: 'Beta-blocker',
  C: 'Calcium-channel blocker',
  D: 'Diuretic',
  MRA: 'Mineralocorticoid receptor antagonist',
  SGLT2i: 'SGLT2 inhibitor',
  GLP1RA: 'GLP-1 receptor agonist',
  Others: 'Other medicine',
} as const

export function groupDisplay(group: FinalRegimenComponent['group'], locale: ClinicalDecisionSupportLocale): string {
  return drugClassDisplay(group, GROUP_NAMES[group] || group, locale)
}

export function groupNameDisplay(group: FinalRegimenComponent['group'], locale: ClinicalDecisionSupportLocale): string {
  const display = groupDisplay(group, locale)
  const prefix = `${group.toUpperCase()} · `
  return display.startsWith(prefix) ? display.slice(prefix.length) : display
}

export function recommendedDoseSummary(
  component: FinalRegimenComponent,
  catalog: Record<string, RegimenMedicine[]>,
): string {
  void catalog
  return component.dose
}

export function activeDose(strategy: string): 'low' | 'usual' | 'max' {
  const normalized = strategy.toLocaleLowerCase()
  if (normalized.includes('maximum') || normalized.includes('tối đa')) return 'max'
  if (normalized.includes('usual') || normalized.includes('thông thường')) return 'usual'
  return 'low'
}

export function componentMedicines(
  component: FinalRegimenComponent,
  catalog: Record<string, RegimenMedicine[]>,
): RegimenMedicine[] {
  const allMedicines = catalog.__all__ ?? Array.from(
    new Map(Object.values(catalog).flat().map((medicine) => [medicine.id || medicine.name, medicine])).values(),
  )
  const grouped = catalog[component.group]
  const groupMedicines = grouped && grouped.length > 0
    ? grouped
    : allMedicines.filter((medicine) => medicineInGroup(medicine, component.group))
  if (component.medicineId) return allMedicines.filter((medicine) => medicine.id === component.medicineId)
  const subgroup = component.subgroup
  if (subgroup) {
    return groupMedicines.filter((medicine) => subgroupMatches(medicine.subgroup, subgroup))
  }
  if (!isSpecific(component)) return groupMedicines
  const label = component.label.toLocaleLowerCase()
  return allMedicines.filter((medicine) => {
    const name = medicine.name.toLocaleLowerCase()
    return name === label || label.includes(name)
  })
}

export function componentSubgroups(
  component: FinalRegimenComponent,
  catalog: Record<string, RegimenMedicine[]>,
): string[] {
  return Array.from(new Set(componentMedicines(component, catalog).map((medicine) => medicine.subgroup).filter(Boolean)))
}

function medicineInGroup(medicine: RegimenMedicine, group: FinalRegimenComponent['group']): boolean {
  if (group === 'MRA') return medicine.subgroup.toLocaleUpperCase().includes('MRA')
  if (group === 'Others') {
    return !['A', 'B', 'C', 'D', 'SGLT2i'].includes(medicine.group)
  }
  return medicine.group.toLocaleLowerCase() === group.toLocaleLowerCase()
}

export function isSpecific(component: FinalRegimenComponent): boolean {
  if (component.selectorKind === 'group') return Boolean(component.subgroup)
  return Boolean(component.subgroup)
    || component.label.toLocaleLowerCase() !== component.group.toLocaleLowerCase()
}
