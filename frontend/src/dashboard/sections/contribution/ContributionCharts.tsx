import { Code2, GitCommitHorizontal } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ContributorMetric } from '../../../api/types'
import { ChartTooltip } from '../../charts/ChartTooltip'

const MEMBER_COLORS = [
  '#0891b2', // cyan
  '#8b5cf6', // purple
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ec4899', // pink
  '#3b82f6', // blue
  '#6366f1', // indigo
]

interface ContributionChartsProps {
  contributors: ContributorMetric[]
}

export function ContributionCharts({ contributors }: ContributionChartsProps) {
  const commitData = contributors.map((c) => ({
    label: c.display_name,
    commits: c.commits,
    percentage: c.commits_percentage,
  }))

  const locData = contributors.map((c) => ({
    label: c.display_name,
    added: c.lines_added,
    deleted: c.lines_deleted,
  }))

  return (
    <div className="contrib-grid-2">
      {/* Chart 1: Commit Share Distribution */}
      <div className="contrib-chart-card">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <GitCommitHorizontal size={18} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white m-0">Commit Distribution by Author</h4>
            <p className="text-xs text-gray-400 m-0">Total commit count breakdown per contributor</p>
          </div>
        </div>

        <div className="contrib-chart-wrapper">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={commitData} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid stroke="var(--border-soft)" horizontal={false} />
              <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis
                type="category"
                dataKey="label"
                width={100}
                tick={{ fill: 'var(--text-secondary)', fontSize: 12, fontWeight: 500 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: 'var(--accent-divider-soft)' }}
                content={
                  <ChartTooltip
                    formatValue={(v) => `${v} commits`}
                  />
                }
              />
              <Bar dataKey="commits" name="Commits" radius={[0, 6, 6, 0]} maxBarSize={22}>
                {commitData.map((_, idx) => (
                  <Cell key={idx} fill={MEMBER_COLORS[idx % MEMBER_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 2: Code Churn (Lines Added vs Deleted) */}
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
  )
}
