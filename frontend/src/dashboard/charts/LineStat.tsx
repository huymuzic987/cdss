import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_SERIES } from '../chartColors'
import { ChartTooltip } from './ChartTooltip'

interface Series {
  key: string
  label: string
}

interface LineStatProps {
  data: Record<string, number | string>[]
  /** Second+ line series, for genuinely multi-series data (e.g. systolic vs.
   * diastolic on the same mmHg axis). Single-line callers omit this and pass
   * `{ label, value }[]` data as before. */
  series?: Series[]
  formatValue?: (value: number) => string
  height?: number
  yDomain?: [number, number]
}

export function LineStat({ data, series, formatValue, height = 220, yDomain }: LineStatProps) {
  const lines = series ?? [{ key: 'value', label: '' }]
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-soft)" strokeDasharray="0" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis
          domain={yDomain ?? ['auto', 'auto']}
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<ChartTooltip formatValue={formatValue as (v: number | string) => string} />} />
        {lines.map((line, i) => {
          const color = series ? CHART_SERIES[i % CHART_SERIES.length] : 'var(--accent-solid)'
          return (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.label || undefined}
              stroke={color}
              strokeWidth={2}
              dot={{ r: 4, fill: color, stroke: 'var(--bg-panel)', strokeWidth: 2 }}
              activeDot={{ r: 5 }}
            />
          )
        })}
      </LineChart>
    </ResponsiveContainer>
  )
}
