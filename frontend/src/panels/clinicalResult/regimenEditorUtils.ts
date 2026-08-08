import type { CatalogGroup, CatalogMedicine } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, RegimenMedicine } from '../clinicalPresentation/types'
import { explicitSubgroupMatches, subgroupMatches } from '../clinicalPresentation/regimenCatalog'
import type { DragSelection } from './regimenEditorTypes'
import type { RegimenComponentKind } from './RegimenComponentSummary'
import { groupDisplay, groupNameDisplay } from './RegimenCatalog'

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

function normalized(value: string): string {
  return value.toLocaleLowerCase().normalize('NFKD').replace(/\p{M}/gu, '').trim()
}

function isMedicineComponent(component: FinalRegimenComponent): boolean {
  return Boolean(component.medicineId)
    || component.selectorKind === 'medicine'
    || (!component.selectorKind && !component.subgroup && normalized(component.label) !== normalized(component.group))
}

function findMedicine(component: FinalRegimenComponent, group: CatalogGroup | undefined): CatalogMedicine | undefined {
  const medicines = group?.subgroups.flatMap((item) => item.medicines) ?? []
  if (component.medicineId) return medicines.find((medicine) => medicine.drug_id === component.medicineId)
  if (!isMedicineComponent(component)) return undefined
  const label = normalized(component.label)
  return medicines.find((medicine) => {
    const name = normalized(medicine.name)
    return name === label || label.includes(name)
  })
}

function medicineComponent(medicine: CatalogMedicine): FinalRegimenComponent {
  return {
    label: medicine.name, detail: medicine.subgroup ?? medicine.group_code,
    group: groupFor(medicine.group_code), dose: medicine.dose_low ?? 'Low dose',
    ...(medicine.subgroup ? { subgroup: medicine.subgroup } : {}),
    selectorKind: 'medicine', medicineId: medicine.drug_id, doseStrategy: 'LOW_DOSE', isCustom: true,
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
      subgroup: selection.subgroup, selectorKind: 'subgroup', doseStrategy: 'LOW_DOSE', isCustom: true,
    }
  }
  return { label: group.label_en, detail: group.label_en, group: groupFor(group.code), dose: 'Low dose', selectorKind: 'group', doseStrategy: 'LOW_DOSE', isCustom: true }
}

export function displayComponent(component: FinalRegimenComponent, catalog: CatalogGroup[], locale: ClinicalDecisionSupportLocale) {
  const group = catalog.find((item) => item.code === component.group)
  const medicine = findMedicine(component, group)
  if (medicine) return { ...component, label: medicine.name, detail: medicine.subgroup ?? component.detail }
  if (isMedicineComponent(component)) return component
  return { ...component, label: locale === 'vi' ? (group?.label_vi ?? component.label) : (group?.label_en ?? component.label) }
}

export function editorPresentationCatalog(catalog: CatalogGroup[]): Record<string, RegimenMedicine[]> {
  return Object.fromEntries(catalog.map((group) => [
    group.code,
    group.subgroups.flatMap((subgroup) => subgroup.medicines.map((medicine) => ({
      id: medicine.drug_id,
      name: medicine.name,
      group: medicine.group_code,
      subgroup: medicine.subgroup ?? '',
      route: medicine.route ?? '',
      doseLow: medicine.dose_low ?? '',
      doseUsual: medicine.dose_usual ?? '',
      doseMax: medicine.dose_max ?? '',
      snomedCode: medicine.snomed_code ?? '',
    }))),
  ]))
}

function subgroupText(subgroups: string[], locale: ClinicalDecisionSupportLocale): string {
  return subgroups.length > 0
    ? `${locale === 'vi' ? 'Phân nhóm' : 'Subgroups'}: ${subgroups.join(' / ')}`
    : (locale === 'vi' ? 'Không có phân nhóm hiện tại' : 'No current subgroups')
}

export function editorComponentSummary(
  component: FinalRegimenComponent,
  catalog: CatalogGroup[],
  locale: ClinicalDecisionSupportLocale,
  currentSubgroups: Record<string, string[]> = {},
): { kind: RegimenComponentKind, label: string, clarification: string, subgroups: string, dose: string, groupCode: string, subgroupLabel: string } {
  const displayed = displayComponent(component, catalog, locale)
  const group = catalog.find((item) => item.code === component.group)
  const groupClarification = groupNameDisplay(component.group, locale)
  const medicine = findMedicine(component, group)
  const kind: RegimenComponentKind = isMedicineComponent(component) ? 'medicine' : component.subgroup || component.selectorKind === 'subgroup' ? 'subgroup' : 'group'
  const availableSubgroups = currentSubgroups[component.group] ?? group?.subgroups.map((item) => item.name) ?? []
  const subgroupMatcher = component.isCustom ? explicitSubgroupMatches : subgroupMatches
  const selectedSubgroups = component.subgroup
    ? availableSubgroups.filter((name) => subgroupMatcher(name, component.subgroup ?? ''))
    : availableSubgroups
  if (kind === 'medicine') {
    const dose = component.doseStrategy === 'MAX_DOSE' ? medicine?.dose_max : component.doseStrategy === 'USUAL_DOSE' ? medicine?.dose_usual : medicine?.dose_low
    return {
      kind,
      label: medicine?.name ?? displayed.label,
      clarification: groupDisplay(component.group, locale),
      subgroups: subgroupText(medicine?.subgroup ? [medicine.subgroup] : selectedSubgroups, locale),
      dose: dose || displayed.dose,
      groupCode: component.group,
      subgroupLabel: medicine?.subgroup ?? selectedSubgroups.join(' / '),
    }
  }
  return {
    kind,
    label: component.group,
    clarification: groupClarification,
    subgroups: subgroupText(selectedSubgroups, locale),
    dose: displayed.dose,
    groupCode: component.group,
    subgroupLabel: selectedSubgroups.join(' / '),
  }
}
