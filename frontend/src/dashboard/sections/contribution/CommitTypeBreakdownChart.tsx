import { Layers } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { CommitHistoryItem, ContributorMetric } from '../../../api/types'
import { ChartTooltip } from '../../charts/ChartTooltip'
import { buildCommitTypeData } from './commitChartData'

interface CommitTypeBreakdownChartProps {
  contributors: ContributorMetric[]
  commitHistory?: CommitHistoryItem[]
}

export function CommitTypeBreakdownChart({ contributors, commitHistory = [] }: CommitTypeBreakdownChartProps) {
  const chartData = buildCommitTypeData(contributors, commitHistory)

  return (
    <div className="contrib-chart-card">
      <div className="flex items-center gap-2">
        <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
          <Layers size={18} />
        </div>
        <div>
          <h4 className="text-sm font-bold text-white m-0">Commit Type Breakdown</h4>
          <p className="text-xs text-gray-400 m-0">Categorized by Feat, Fix, Refactor &amp; Maintenance</p>
        </div>
      </div>

      <div className="contrib-chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid stroke="var(--border-soft)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: 'var(--accent-divider-soft)' }}
              content={
                <ChartTooltip
                  formatValue={(v) => `${v} commits`}
                />
              }
            />
            <Legend wrapperStyle={{ paddingTop: '8px', fontSize: '11px' }} iconType="circle" />
            <Bar dataKey="Feature" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} maxBarSize={28} />
            <Bar dataKey="Fix" stackId="a" fill="#f43f5e" radius={[0, 0, 0, 0]} maxBarSize={28} />
            <Bar dataKey="Refactor" stackId="a" fill="#8b5cf6" radius={[0, 0, 0, 0]} maxBarSize={28} />
            <Bar dataKey="Maintenance" stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
