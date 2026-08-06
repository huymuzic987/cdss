import type { FinalRegimenComponent, FinalRegimenOption } from './types'

function regimenOptionIdentity(components: FinalRegimenComponent[]): string {
  return JSON.stringify(
    components
      .map((component) => ({
        group: component.group,
        label: component.label.toLocaleLowerCase(),
        dose: component.dose.toLocaleLowerCase(),
        subgroup: component.subgroup?.toLocaleLowerCase() ?? '',
      }))
      .sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right))),
  )
}

export function uniqueRegimenOptions(options: FinalRegimenOption[]): FinalRegimenOption[] {
  const uniqueOptions = new Map<string, FinalRegimenOption>()
  for (const option of options) {
    const identity = regimenOptionIdentity(option.components)
    if (!uniqueOptions.has(identity)) uniqueOptions.set(identity, option)
  }
  return [...uniqueOptions.values()].map((option, index) => ({
    ...option,
    id: `regimen-option-${index + 1}`,
  }))
}
