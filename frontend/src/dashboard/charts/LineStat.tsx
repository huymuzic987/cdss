import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartTooltip } from './ChartTooltip'

interface LineStatProps {
  data: { label: string; value: number }[]
  formatValue?: (value: number) => string
  height?: number
  yDomain?: [number, number]
}

export function LineStat({ data, formatValue, height = 220, yDomain }: LineStatProps) {
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
        <Line
          type="monotone"
          dataKey="value"
          stroke="var(--accent-solid)"
          strokeWidth={2}
          dot={{ r: 4, fill: 'var(--accent-solid)', stroke: 'var(--bg-panel)', strokeWidth: 2 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
