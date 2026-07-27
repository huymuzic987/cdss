// Chart color roles, validated against this app's actual panel surfaces
// (dark #090d16, light #f3f5f7) with the dataviz skill's palette validator.
// CSS vars so the same component works in both themes without knowing which
// one is active (mirrors how BarStat/LineStat already read `--accent-solid`).

/** Two-series comparisons (e.g. systolic vs. diastolic). Fixed order, never cycled. */
export const CHART_SERIES = ['var(--chart-series-1)', 'var(--chart-series-2)'] as const

/** One-hue ramp for ordinal buckets (age bands, severity stages, risk levels) --
 * darker/more saturated = later in the sequence, so color reinforces order
 * instead of just decorating it. */
const ORDINAL_RAMP = [
  'var(--chart-ordinal-1)',
  'var(--chart-ordinal-2)',
  'var(--chart-ordinal-3)',
  'var(--chart-ordinal-4)',
  'var(--chart-ordinal-5)',
]

export function ordinalColor(index: number): string {
  return ORDINAL_RAMP[Math.min(index, ORDINAL_RAMP.length - 1)]
}

/** Fixed per-section hues -- each dashboard section that isn't ordinal (and
 * so doesn't use `ordinalColor`) gets its own single flat hue from the
 * validated categorical set, so the dashboard reads as many distinct
 * sections rather than one repeated accent color. Never mix two of these
 * within the same chart. */
/** Repeats a single flat section hue once per bar, for BarStat's `colors`
 * prop -- keeps every bar in a section the same identity color while still
 * using the shared per-bar `<Cell>` coloring mechanism. */
export function flatColors(color: string, length: number): string[] {
  return Array(length).fill(color)
}

export const SECTION_COLORS = {
  comorbidities: 'var(--chart-violet)',
  riskFactorCount: 'var(--chart-red)',
  age: 'var(--chart-orange)',
  drugClasses: 'var(--chart-teal)',
  adherenceYes: 'var(--chart-violet)',
  adherenceNo: 'var(--chart-neutral)',
} as const
