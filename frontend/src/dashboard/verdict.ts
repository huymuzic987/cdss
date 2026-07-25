export type VerdictStatus = 'success' | 'warning' | 'danger'

export interface Verdict {
  status: VerdictStatus
  badge: string
}

/** Higher is better (e.g. on-schedule rate, adherence rate). */
export function rateVerdict(value: number, goodAt: number, watchAt: number): Verdict {
  if (value >= goodAt) return { status: 'success', badge: 'On track' }
  if (value >= watchAt) return { status: 'warning', badge: 'Watch' }
  return { status: 'danger', badge: 'Needs attention' }
}

/** Lower is better (e.g. early revisit rate). */
export function inverseRateVerdict(value: number, goodBelow: number, watchBelow: number): Verdict {
  if (value <= goodBelow) return { status: 'success', badge: 'On track' }
  if (value <= watchBelow) return { status: 'warning', badge: 'Watch' }
  return { status: 'danger', badge: 'Needs attention' }
}
