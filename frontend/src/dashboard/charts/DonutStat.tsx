import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { ChartTooltip } from './ChartTooltip'

interface DonutSlice {
  label: string
  value: number
  color: string
}

interface DonutStatProps {
  slices: DonutSlice[]
  centerLabel: string
  height?: number
}

/** Two-ish-slice donut with a centered headline number and a text legend
 * below (never color-only identity -- see the dataviz skill's legend rule). */
export function DonutStat({ slices, centerLabel, height = 200 }: DonutStatProps) {
  const total = slices.reduce((sum, s) => sum + s.value, 0)
  return (
    <div>
      <div style={{ position: 'relative', height }}>
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="label"
              innerRadius="65%"
              outerRadius="90%"
              stroke="var(--bg-panel)"
              strokeWidth={2}
            >
              {slices.map((s, i) => (
                <Cell key={i} fill={s.color} />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip formatValue={(v) => `${v} (${((Number(v) / total) * 100).toFixed(0)}%)`} />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="dash-donut-center">
          <span className="dash-donut-center-value">{centerLabel}</span>
        </div>
      </div>
      <div className="dash-chart-legend">
        {slices.map((s, i) => (
          <span key={i} className="dash-chart-legend-item">
            <span className="dash-chart-legend-swatch" style={{ background: s.color }} />
            {s.label} ({s.value})
          </span>
        ))}
      </div>
    </div>
  )
}
