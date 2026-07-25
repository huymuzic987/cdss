interface TooltipPayloadEntry {
  name?: string
  value?: number | string
  color?: string
}

interface ChartTooltipProps {
  active?: boolean
  label?: string | number
  payload?: TooltipPayloadEntry[]
  formatValue?: (value: number | string) => string
}

export function ChartTooltip({ active, label, payload, formatValue }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="dash-tooltip">
      {label !== undefined && <div className="dash-tooltip-label">{label}</div>}
      {payload.map((entry, i) => (
        <div key={i} className="dash-tooltip-row">
          {entry.color && <span className="dash-tooltip-key" style={{ background: entry.color }} />}
          <span className="dash-tooltip-name">{entry.name}</span>
          <span className="dash-tooltip-value">
            {entry.value !== undefined ? (formatValue ? formatValue(entry.value) : entry.value) : ''}
          </span>
        </div>
      ))}
    </div>
  )
}
