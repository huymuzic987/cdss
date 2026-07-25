import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartTooltip } from './ChartTooltip'

interface BarStatProps {
  data: { label: string; value: number }[]
  layout?: 'horizontal' | 'vertical'
  formatValue?: (value: number) => string
  height?: number
  labelWidth?: number
}

export function BarStat({ data, layout = 'horizontal', formatValue, height = 220, labelWidth = 160 }: BarStatProps) {
  const isVertical = layout === 'vertical'
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout={isVertical ? 'vertical' : 'horizontal'}
        margin={{ top: 4, right: 12, bottom: 0, left: isVertical ? 8 : 0 }}
      >
        <CartesianGrid
          stroke="var(--border-soft)"
          strokeDasharray="0"
          horizontal={!isVertical}
          vertical={isVertical}
        />
        {isVertical ? (
          <>
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="label"
              width={labelWidth}
              tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
          </>
        )}
        <Tooltip
          cursor={{ fill: 'var(--accent-divider-soft)' }}
          content={<ChartTooltip formatValue={formatValue as (v: number | string) => string} />}
        />
        <Bar dataKey="value" fill="var(--accent-solid)" radius={isVertical ? [0, 4, 4, 0] : [4, 4, 0, 0]} maxBarSize={24} />
      </BarChart>
    </ResponsiveContainer>
  )
}
