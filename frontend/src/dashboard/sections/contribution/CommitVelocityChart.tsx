import { Activity } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ContributorMetric, RecentCommitItem } from '../../../api/types'
import { ChartTooltip } from '../../charts/ChartTooltip'

export function CommitVelocityChart({
  contributors = [],
  recentCommits = [],
}: {
  contributors?: ContributorMetric[]
  recentCommits?: RecentCommitItem[]
}) {
  const [viewMode, setViewMode] = useState<'daily' | 'cumulative'>('daily')

  const chartData = useMemo(() => {
    if (!recentCommits || recentCommits.length === 0) return []

    // Group commits by date formatted MMM DD
    const countsByDate = new Map<string, number>()
    const sorted = [...recentCommits].sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))

    sorted.forEach((item) => {
      const dateStr = item.timestamp
        ? new Date(item.timestamp * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        : 'Recent'
      countsByDate.set(dateStr, (countsByDate.get(dateStr) || 0) + 1)
    })

    const entries = Array.from(countsByDate.entries())
    const totalRepoCommits = contributors.reduce((acc, c) => acc + c.commits, 0)
    const baseline = Math.max(0, totalRepoCommits - recentCommits.length)

    let runningSum = baseline
    return entries.map(([date, count]) => {
      runningSum += count
      return {
        date,
        commits: count,
        cumulative: runningSum,
      }
    })
  }, [contributors, recentCommits])

  return (
    <div className="contrib-chart-card">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Activity size={18} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white m-0">Commit Activity Velocity</h4>
            <p className="text-xs text-gray-400 m-0">Timeline velocity &amp; commit stream</p>
          </div>
        </div>

        <div className="flex items-center gap-1 bg-black/40 border border-white/10 p-1 rounded-lg text-xs">
          <button
            type="button"
            onClick={() => setViewMode('daily')}
            className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${viewMode === 'daily' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            Daily Velocity
          </button>
          <button
            type="button"
            onClick={() => setViewMode('cumulative')}
            className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${viewMode === 'cumulative' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            Cumulative
          </button>
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
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
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
              dataKey={viewMode === 'daily' ? 'commits' : 'cumulative'}
              name={viewMode === 'daily' ? 'Daily Commits' : 'Cumulative Total'}
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
