export const pct = (value: number) => `${(value * 100).toFixed(1)}%`

export const compact = (value: number) =>
  new Intl.NumberFormat(undefined, { notation: 'compact' }).format(value)

export const mmHg = (value: number | null) =>
  value === null ? 'No data' : `${value.toFixed(1)} mmHg`
