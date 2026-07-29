import type { JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { ActionOption, RecommendedDrugClass, RecommendedOrder } from './types'
import { humanize, localized, objectValue, stringValue } from './values'

interface Medicine {
  drugId: string
  name: string
  dose: string
  classLabel: string
}

function parseMedicine(value: JsonValue): Medicine | null {
  const medicine = objectValue(value)
  if (!medicine || medicine.available === false) return null
  const name = stringValue(medicine.name, stringValue(medicine.drug_name))
  if (!name) return null
  return {
    drugId: stringValue(medicine.drug_id, stringValue(medicine.id)),
    name,
    dose: stringValue(medicine.starting_dose, stringValue(medicine.dose_low, stringValue(medicine.dose))),
    classLabel: stringValue(medicine.class_label, stringValue(medicine.subgroup, stringValue(medicine.drug_class))),
  }
}

export function parseStructuredOrders(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): RecommendedOrder[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((entry, index) => {
    const item = objectValue(entry)
    if (!item) return []
    const components = Array.isArray(item.components)
      ? item.components.map(parseMedicine).filter((medicine): medicine is Medicine => medicine !== null)
      : []
    const name = localized(item, 'name', locale) || components.map((component) => component.name).join(' + ')
    if (!name) return []
    const dose = stringValue(item.starting_dose, stringValue(item.dose))
      || components.map((component) => component.dose).filter(Boolean).join(' + ')
    const classLabel = localized(item, 'class_label', locale)
      || components.map((component) => component.classLabel).filter(Boolean).join(' + ')
    const drugClasses = parseDrugClasses(item.drug_classes, locale)
    return [{
      id: stringValue(item.id, `order-${index}`), name, dose: dose || undefined,
      classLabel: classLabel || undefined,
      orderType: stringValue(item.type, 'order'), sourceData: item,
      medicineIds: components.map((component) => component.drugId).filter(Boolean),
      drugClasses: drugClasses.length > 0 ? drugClasses : undefined,
    }]
  })
}

function parseDrugClasses(
  value: JsonValue | undefined,
  locale: ClinicalDecisionSupportLocale,
): RecommendedDrugClass[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((entry, classIndex) => {
    const drugClass = objectValue(entry)
    if (!drugClass) return []
    const code = stringValue(drugClass.code, String(classIndex + 1))
    const medicines = Array.isArray(drugClass.medicines)
      ? drugClass.medicines.flatMap((rawMedicine, medicineIndex) => {
          const medicine = objectValue(rawMedicine)
          if (!medicine) return []
          const name = stringValue(medicine.name)
          const dose = stringValue(medicine.dose)
          if (!name || !dose) return []
          return [{
            id: stringValue(medicine.id, `${code}-medicine-${medicineIndex}`),
            name,
            dose,
            route: stringValue(medicine.route) || undefined,
            subgroup: stringValue(medicine.subgroup) || undefined,
          }]
        })
      : []
    return [{
      code,
      label: localized(drugClass, 'label', locale) || `${locale === 'vi' ? 'NhÃ³m thuá»‘c' : 'Drug Class'} ${code}`,
      doseLabel: localized(drugClass, 'dose_label', locale),
      medicines,
    }]
  })
}

export function parseOptions(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): ActionOption[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((entry, index) => {
    if (typeof entry === 'string') return [{ id: entry, label: humanize(entry) }]
    const option = objectValue(entry)
    if (!option) return []
    const id = stringValue(option.id, `action-${index}`)
    return [{ id, label: localized(option, 'label', locale) || humanize(id) }]
  })
}

