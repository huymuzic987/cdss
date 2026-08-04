import { PieChart as PieIcon } from 'lucide-react'
import { useState } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { ContributorMetric } from '../../../api/types'
import { ChartTooltip } from '../../charts/ChartTooltip'

const MEMBER_COLORS = [
  '#06b6d4',
  '#8b5cf6',
  '#10b981',
  '#f59e0b',
  '#ec4899',
  '#3b82f6',
  '#6366f1',
]

export function DonutShareChart({ contributors }: { contributors: ContributorMetric[] }) {
  const [metric, setMetric] = useState<'commits' | 'lines_added'>('commits')

  const data = contributors.map((c) => ({
    name: c.display_name,
    value: metric === 'commits' ? c.commits : c.lines_added,
    percentage: metric === 'commits' ? c.commits_percentage : c.lines_added_percentage,
  }))

  return (
    <div className="contrib-chart-card">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <PieIcon size={18} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white m-0">Team Impact Share</h4>
            <p className="text-xs text-gray-400 m-0">Interactive relative share by member</p>
          </div>
        </div>

        <div className="flex items-center gap-1 bg-black/40 border border-white/10 p-1 rounded-lg text-xs">
          <button
            type="button"
            onClick={() => setMetric('commits')}
            className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${metric === 'commits' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            Commits
          </button>
          <button
            type="button"
            onClick={() => setMetric('lines_added')}
            className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${metric === 'lines_added' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            Lines Added
          </button>
        </div>
      </div>

      <div className="contrib-chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              content={
                <ChartTooltip
                  formatValue={(v) => typeof v === 'number' ? `${v.toLocaleString()} ${metric === 'commits' ? 'commits' : 'lines'}` : String(v)}
                />
              }
            />
            <Legend wrapperStyle={{ paddingTop: '8px', fontSize: '11px' }} iconType="circle" />
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={4}
              dataKey="value"
            >
              {data.map((_, idx) => (
                <Cell key={idx} fill={MEMBER_COLORS[idx % MEMBER_COLORS.length]} stroke="rgba(0,0,0,0.4)" strokeWidth={2} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
