import type { FinalRegimenComponent } from './types'

type ParsedComponent = FinalRegimenComponent & { generic?: boolean }

export function componentLabel(item: ParsedComponent): string {
  const base = item.generic || item.detail === item.label
    ? item.label
    : `${item.label} (${item.detail})`
  return item.subgroup ? `${base} (${item.subgroup})` : base
}

export function isStopped(item: ParsedComponent, stop: ParsedComponent): boolean {
  if (item.group !== stop.group) return false
  if (stop.subgroup) {
    return item.subgroup?.toLocaleLowerCase() === stop.subgroup.toLocaleLowerCase()
  }
  return stop.label.toLocaleUpperCase() === item.label.toLocaleUpperCase()
    || (stop.generic === true && item.generic === true)
}
