import { Code, GitCommit, Layers, Users } from 'lucide-react'
import type { ContributionSummary } from '../../../api/types'

export function ContributionMetricsGrid({ summary }: { summary: ContributionSummary }) {
  return (
    <div className="contrib-kpi-grid">
      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5">
            <GitCommit size={15} className="text-cyan-400" /> Total Commits
          </span>
          <span className="text-[10px] font-mono bg-cyan-950/60 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-800/30">
            Git Log
          </span>
        </div>
        <div className="contrib-kpi-value">
          {summary.total_commits}
        </div>
      </div>

      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5">
            <Code size={15} className="text-emerald-400" /> Lines Added
          </span>
          <span className="text-[10px] font-mono bg-emerald-950/60 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-800/30">
            + Insertions
          </span>
        </div>
        <div className="contrib-kpi-value text-emerald-400">
          +{summary.total_lines_added.toLocaleString()}
        </div>
      </div>

      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5">
            <Layers size={15} className="text-purple-400" /> Total LOC Changes
          </span>
          <span className="text-[10px] font-mono bg-purple-950/60 text-purple-300 px-1.5 py-0.5 rounded border border-purple-800/30">
            Volume
          </span>
        </div>
        <div className="contrib-kpi-value text-purple-300">
          {summary.total_loc_changes.toLocaleString()}
        </div>
      </div>

      <div className="contrib-kpi-card group">
        <div className="contrib-kpi-header">
          <span className="flex items-center gap-1.5">
            <Users size={15} className="text-amber-400" /> Active Members
          </span>
          <span className="text-[10px] font-mono bg-amber-950/60 text-amber-300 px-1.5 py-0.5 rounded border border-amber-800/30">
            Contributors
          </span>
        </div>
        <div className="contrib-kpi-value text-amber-300">
          {summary.active_contributors}
        </div>
      </div>
    </div>
  )
}
