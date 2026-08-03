import { Code, GitCommit, Layers, TrendingUp, Users } from 'lucide-react'
import type { ContributionSummary } from '../../../api/types'

export function ContributionMetricsGrid({ summary }: { summary: ContributionSummary }) {
  return (
    <div className="contrib-kpi-grid">
      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5 font-medium">
            <GitCommit size={15} className="text-cyan-400 group-hover:scale-110 transition-transform" /> Total Commits
          </span>
          <span className="text-[10px] font-mono bg-cyan-950/80 text-cyan-300 px-2 py-0.5 rounded-full border border-cyan-800/40 shadow-sm">
            Git Log
          </span>
        </div>
        <div className="flex items-baseline justify-between mt-1">
          <div className="contrib-kpi-value text-white">
            {summary.total_commits}
          </div>
          <span className="text-[11px] text-cyan-400/80 font-mono flex items-center gap-0.5">
            <TrendingUp size={11} /> 100% tracked
          </span>
        </div>
      </div>

      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5 font-medium">
            <Code size={15} className="text-emerald-400 group-hover:scale-110 transition-transform" /> Lines Added
          </span>
          <span className="text-[10px] font-mono bg-emerald-950/80 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-800/40 shadow-sm">
            + Insertions
          </span>
        </div>
        <div className="flex items-baseline justify-between mt-1">
          <div className="contrib-kpi-value text-emerald-400">
            +{summary.total_lines_added.toLocaleString()}
          </div>
          <span className="text-[11px] text-emerald-400/80 font-mono">
            LOC
          </span>
        </div>
      </div>

      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5 font-medium">
            <Layers size={15} className="text-purple-400 group-hover:scale-110 transition-transform" /> Total LOC Changes
          </span>
          <span className="text-[10px] font-mono bg-purple-950/80 text-purple-300 px-2 py-0.5 rounded-full border border-purple-800/40 shadow-sm">
            Volume
          </span>
        </div>
        <div className="flex items-baseline justify-between mt-1">
          <div className="contrib-kpi-value text-purple-300">
            {summary.total_loc_changes.toLocaleString()}
          </div>
          <span className="text-[11px] text-purple-400/80 font-mono">
            Churn
          </span>
        </div>
      </div>

      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5 font-medium">
            <Users size={15} className="text-amber-400 group-hover:scale-110 transition-transform" /> Active Members
          </span>
          <span className="text-[10px] font-mono bg-amber-950/80 text-amber-300 px-2 py-0.5 rounded-full border border-amber-800/40 shadow-sm">
            Contributors
          </span>
        </div>
        <div className="flex items-baseline justify-between mt-1">
          <div className="contrib-kpi-value text-amber-300">
            {summary.active_contributors}
          </div>
          <span className="text-[11px] text-amber-400/80 font-mono">
            Authors
          </span>
        </div>
      </div>
    </div>
  )
}
