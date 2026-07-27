import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartTooltip } from './ChartTooltip'

interface BarStatProps {
  data: { label: string; value: number }[]
  layout?: 'horizontal' | 'vertical'
  formatValue?: (value: number) => string
  height?: number
  labelWidth?: number
  /** Per-bar colors, in data order (e.g. an ordinal severity ramp). Omit for
   * a plain single-hue bar chart -- never assign rainbow colors to a nominal
   * single-series chart, that spends the identity channel on nothing. */
  colors?: string[]
  /** Always-visible value labels. Required (not just a hover tooltip) for
   * any chart using a hue that falls below 3:1 contrast on the light-theme
   * surface -- see the dataviz skill's "relief channel" requirement. */
  showValueLabels?: boolean
}

export function BarStat({
  data,
  layout = 'horizontal',
  formatValue,
  height = 220,
  labelWidth = 160,
  colors,
  showValueLabels,
}: BarStatProps) {
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
        <Bar dataKey="value" fill="var(--accent-solid)" radius={isVertical ? [0, 4, 4, 0] : [4, 4, 0, 0]} maxBarSize={24}>
          {colors && data.map((_, i) => <Cell key={i} fill={colors[Math.min(i, colors.length - 1)]} />)}
          {showValueLabels && (
            <LabelList
              dataKey="value"
              position={isVertical ? 'right' : 'top'}
              formatter={(v) => (formatValue ? formatValue(Number(v)) : String(v))}
              fill="var(--text-secondary)"
              fontSize={11}
            />
          )}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
