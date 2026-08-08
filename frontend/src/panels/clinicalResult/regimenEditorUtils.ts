import type { CatalogGroup, CatalogMedicine } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent } from '../clinicalPresentation/types'
import type { DragSelection } from './regimenEditorTypes'

const groupCodes = new Set(['A', 'B', 'C', 'D', 'MRA', 'SGLT2i', 'GLP1RA', 'Others'])

export function componentKey(component: FinalRegimenComponent): string {
  if (component.medicineId) return `medicine:${component.medicineId}`
  return `${component.group}:${component.subgroup ?? ''}`
}

export function strategyLabel(strategy: FinalRegimenComponent['doseStrategy'], locale: ClinicalDecisionSupportLocale): string {
  const labels = {
    LOW_DOSE: { en: 'Low', vi: 'Thấp' },
    USUAL_DOSE: { en: 'Usual', vi: 'Thường dùng' },
    MAX_DOSE: { en: 'Maximum', vi: 'Tối đa' },
  }
  return labels[strategy ?? 'LOW_DOSE'][locale]
}

function groupFor(code: string): FinalRegimenComponent['group'] {
  return groupCodes.has(code) ? code as FinalRegimenComponent['group'] : 'Others'
}

function medicineComponent(medicine: CatalogMedicine): FinalRegimenComponent {
  return {
    label: medicine.name, detail: medicine.subgroup ?? medicine.group_code,
    group: groupFor(medicine.group_code), dose: medicine.dose_low ?? 'Low dose',
    ...(medicine.subgroup ? { subgroup: medicine.subgroup } : {}),
    selectorKind: 'medicine', medicineId: medicine.drug_id, doseStrategy: 'LOW_DOSE',
  }
}

export function selectionComponent(selection: DragSelection, catalog: CatalogGroup[]): FinalRegimenComponent | null {
  const group = catalog.find((item) => item.code === selection.groupCode)
  if (!group) return null
  if (selection.selectorKind === 'medicine' && selection.medicineId) {
    const medicine = group.subgroups.flatMap((item) => item.medicines).find((item) => item.drug_id === selection.medicineId)
    return medicine ? medicineComponent(medicine) : null
  }
  if (selection.selectorKind === 'subgroup' && selection.subgroup) {
    return {
      label: group.label_en, detail: selection.subgroup, group: groupFor(group.code), dose: 'Low dose',
      subgroup: selection.subgroup, selectorKind: 'subgroup', doseStrategy: 'LOW_DOSE',
    }
  }
  return { label: group.label_en, detail: group.label_en, group: groupFor(group.code), dose: 'Low dose', selectorKind: 'group', doseStrategy: 'LOW_DOSE' }
}

export function displayComponent(component: FinalRegimenComponent, catalog: CatalogGroup[], locale: ClinicalDecisionSupportLocale) {
  const group = catalog.find((item) => item.code === component.group)
  if (component.medicineId) {
    const medicine = group?.subgroups.flatMap((item) => item.medicines).find((item) => item.drug_id === component.medicineId)
    return medicine ? { ...component, label: medicine.name, detail: medicine.subgroup ?? component.detail } : component
  }
  return { ...component, label: locale === 'vi' ? (group?.label_vi ?? component.label) : (group?.label_en ?? component.label) }
}
