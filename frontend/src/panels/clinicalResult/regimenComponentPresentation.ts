import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, RegimenMedicine } from '../clinicalPresentation/types'
import { componentSubgroups, componentMedicines, groupDisplay, groupNameDisplay, isSpecific } from './RegimenCatalog'
import type { RegimenComponentKind } from './RegimenComponentSummary'

export function componentKind(component: FinalRegimenComponent): RegimenComponentKind {
  if (component.medicineId || component.selectorKind === 'medicine' || (isSpecific(component) && component.label !== component.group)) return 'medicine'
  if (component.subgroup || component.selectorKind === 'subgroup') return 'subgroup'
  return 'group'
}

function medicineDose(component: FinalRegimenComponent, medicine: RegimenMedicine): string {
  const normalizedDose = component.dose.toLocaleLowerCase()
  const doseKey = component.doseStrategy === 'MAX_DOSE' || normalizedDose.includes('maximum') ? 'doseMax'
    : component.doseStrategy === 'USUAL_DOSE' || normalizedDose.includes('usual') ? 'doseUsual'
      : component.doseStrategy === 'LOW_DOSE' || normalizedDose.includes('low') ? 'doseLow' : undefined
  return doseKey ? medicine[doseKey] || component.dose : component.dose
}

function subgroupText(subgroups: string[], locale: ClinicalDecisionSupportLocale): string {
  return subgroups.length > 0
    ? `${locale === 'vi' ? 'Phân nhóm' : 'Subgroups'}: ${subgroups.join(' / ')}`
    : (locale === 'vi' ? 'Không có phân nhóm hiện tại' : 'No current subgroups')
}

export function componentSummary(component: FinalRegimenComponent, catalog: Record<string, RegimenMedicine[]>, locale: ClinicalDecisionSupportLocale) {
  const kind = componentKind(component)
  const medicine = kind === 'medicine' ? componentMedicines(component, catalog)[0] : undefined
  const groupName = groupNameDisplay(component.group, locale)
  const groupDisplayText = groupDisplay(component.group, locale)
  const currentSubgroups = componentSubgroups(component, catalog)
  if (kind === 'medicine') {
    return {
      kind,
      label: medicine?.name || component.label,
      compactLabel: medicine?.name || component.label,
      clarification: groupDisplayText,
      subgroups: subgroupText(currentSubgroups, locale),
      dose: medicine ? medicineDose(component, medicine) : component.dose,
    }
  }
  if (kind === 'subgroup') return {
    kind,
    label: component.group,
    compactLabel: component.group,
    clarification: groupName,
    subgroups: subgroupText(currentSubgroups, locale),
    dose: component.dose,
  }
  return {
    kind,
    label: component.label,
    compactLabel: component.group,
    clarification: groupName,
    subgroups: subgroupText(currentSubgroups, locale),
    dose: component.dose,
  }
}
