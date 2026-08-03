import { Code2 } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ContributorMetric, RecentCommitItem } from '../../../api/types'
import { ChartTooltip } from '../../charts/ChartTooltip'
import { CommitTypeBreakdownChart } from './CommitTypeBreakdownChart'
import { CommitVelocityChart } from './CommitVelocityChart'
import { DonutShareChart } from './DonutShareChart'

interface ContributionChartsProps {
  contributors: ContributorMetric[]
  recentCommits?: RecentCommitItem[]
}

export function ContributionCharts({ contributors, recentCommits = [] }: ContributionChartsProps) {
  const locData = contributors.map((c) => ({
    label: c.display_name,
    added: c.lines_added,
    deleted: c.lines_deleted,
  }))

  return (
    <div className="space-y-6">
      <div className="contrib-grid-2">
        {/* Top Row Chart 1: Interactive Donut Share Chart */}
        <DonutShareChart contributors={contributors} />

        {/* Top Row Chart 2: Interactive Commit Velocity Area Chart */}
        <CommitVelocityChart recentCommits={recentCommits} />

        {/* Bottom Row Chart 3: Commit Type Breakdown Stacked Bar Chart */}
        <CommitTypeBreakdownChart contributors={contributors} recentCommits={recentCommits} />

        {/* Bottom Row Chart 4: Code Churn (Lines Added vs Deleted) */}
        <div className="contrib-chart-card">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Code2 size={18} />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white m-0">Code Churn Breakdown</h4>
              <p className="text-xs text-gray-400 m-0">Lines Added (+) vs Lines Deleted (-)</p>
            </div>
          </div>

          <div className="contrib-chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={locData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid stroke="var(--border-soft)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: 'var(--accent-divider-soft)' }}
                  content={
                    <ChartTooltip
                      formatValue={(v) => typeof v === 'number' ? v.toLocaleString() : String(v)}
                    />
                  }
                />
                <Legend
                  wrapperStyle={{ paddingTop: '8px', fontSize: '11px' }}
                  iconType="circle"
                />
                <Bar dataKey="added" name="Lines Added (+)" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={20} />
                <Bar dataKey="deleted" name="Lines Deleted (-)" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
