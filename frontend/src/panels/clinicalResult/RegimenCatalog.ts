import type { FinalRegimenComponent, RegimenMedicine } from '../clinicalPresentation/types'

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

export function recommendedDoseSummary(
  component: FinalRegimenComponent,
  catalog: Record<string, RegimenMedicine[]>,
): string {
  if (!isSpecific(component)) return component.dose
  const doseKey = activeDose(component.dose)
  const doses = Array.from(new Set(componentMedicines(component, catalog).map((medicine) => (
    doseKey === 'max' ? medicine.doseMax : doseKey === 'usual' ? medicine.doseUsual : medicine.doseLow
  )).filter(Boolean)))
  return doses.length > 0 ? doses.join(' / ') : component.dose
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
  if (!isSpecific(component)) {
    const grouped = catalog[component.group]
    if (grouped && grouped.length > 0) return grouped
    return allMedicines.filter((medicine) => medicineInGroup(medicine, component.group))
  }
  const label = component.label.toLocaleLowerCase()
  return allMedicines.filter((medicine) => {
    const name = medicine.name.toLocaleLowerCase()
    return name === label || label.includes(name)
  })
}

function medicineInGroup(medicine: RegimenMedicine, group: FinalRegimenComponent['group']): boolean {
  if (group === 'MRA') return medicine.subgroup.toLocaleUpperCase().includes('MRA')
  if (group === 'Others') {
    return !['A', 'B', 'C', 'D', 'SGLT2i'].includes(medicine.group)
  }
  return medicine.group.toLocaleLowerCase() === group.toLocaleLowerCase()
}

export function isSpecific(component: FinalRegimenComponent): boolean {
  return component.label.toLocaleLowerCase() !== component.group.toLocaleLowerCase()
}
