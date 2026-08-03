import { GitMerge, Layers, Users } from 'lucide-react'
import type { OverlappingTask } from '../../../api/types'

export function OverlappingMatrixTable({ matrix }: { matrix: OverlappingTask[] }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <GitMerge size={18} />
          </div>
          <span>Overlapping Features & Shared Deliverables</span>
        </h3>
        <span className="text-xs text-gray-400 font-mono">
          {matrix.length} Cross-Member Collaboration Domain{matrix.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="contrib-table-container shadow-md">
        <table className="contrib-table">
          <thead>
            <tr>
              <th className="min-w-[200px]">Feature Area</th>
              <th className="min-w-[220px]">Collaborating Members</th>
              <th className="min-w-[300px]">Shared Deliverable Breakdown</th>
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, idx) => (
              <tr key={idx} className="group">
                <td className="font-bold text-white group-hover:text-purple-300 transition-colors">
                  <div className="flex items-center gap-2">
                    <Layers size={15} className="text-purple-400 shrink-0" />
                    <span>{row.feature_area}</span>
                  </div>
                </td>
                <td>
                  <div className="flex flex-wrap gap-1.5">
                    {row.collaborators.map((author, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-purple-950/70 border border-purple-700/40 text-purple-200 text-xs font-medium shadow-sm"
                      >
                        <Users size={11} className="text-purple-400" />
                        <span>{author}</span>
                      </span>
                    ))}
                  </div>
                </td>
                <td className="text-gray-300 leading-relaxed font-sans">
                  <div className="bg-black/30 p-2.5 rounded-lg border border-white/5">
                    {row.shared_deliverables}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
