import { Activity } from 'lucide-react'
import { useMemo } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { RecentCommitItem } from '../../../api/types'
import { ChartTooltip } from '../../charts/ChartTooltip'

export function CommitVelocityChart({ recentCommits }: { recentCommits: RecentCommitItem[] }) {
  const chartData = useMemo(() => {
    if (!recentCommits || recentCommits.length === 0) return []
    // Group commits by date formatted YYYY-MM-DD or sequence
    const countsByDate = new Map<string, number>()
    const sorted = [...recentCommits].sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))

    sorted.forEach((item) => {
      const dateStr = item.timestamp
        ? new Date(item.timestamp * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        : 'Recent'
      countsByDate.set(dateStr, (countsByDate.get(dateStr) || 0) + 1)
    })

    let cumulative = 0
    return Array.from(countsByDate.entries()).map(([date, count]) => {
      cumulative += count
      return {
        date,
        commits: count,
        cumulative,
      }
    })
  }, [recentCommits])

  return (
    <div className="contrib-chart-card">
      <div className="flex items-center gap-2">
        <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <Activity size={18} />
        </div>
        <div>
          <h4 className="text-sm font-bold text-white m-0">Commit Activity Velocity</h4>
          <p className="text-xs text-gray-400 m-0">Timeline velocity &amp; cumulative commit stream</p>
        </div>
      </div>

      <div className="contrib-chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="velocityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--border-soft)" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ stroke: '#3b82f6', strokeWidth: 1, strokeDasharray: '3 3' }}
              content={
                <ChartTooltip
                  formatValue={(v) => `${v} commits`}
                />
              }
            />
            <Area
              type="monotone"
              dataKey="cumulative"
              name="Cumulative Commits"
              stroke="#3b82f6"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#velocityGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
