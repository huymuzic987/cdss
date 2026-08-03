import { CheckCircle2, ExternalLink, GitBranch, GitCommit, Sparkles } from 'lucide-react'
import type { ContributorMetric } from '../../../api/types'

const AVATAR_GRADIENTS = [
  'linear-gradient(135deg, #06b6d4 0%, #2563eb 100%)',
  'linear-gradient(135deg, #a855f7 0%, #4f46e5 100%)',
  'linear-gradient(135deg, #10b981 0%, #0d9488 100%)',
  'linear-gradient(135deg, #f59e0b 0%, #ea580c 100%)',
  'linear-gradient(135deg, #ec4899 0%, #e11d48 100%)',
]

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function ContributorCard({ member, index = 0 }: { member: ContributorMetric; index?: number }) {
  const gradient = AVATAR_GRADIENTS[index % AVATAR_GRADIENTS.length]
  const initials = getInitials(member.display_name)
  const totalLoc = member.lines_added + member.lines_deleted
  const addedRatio = totalLoc > 0 ? (member.lines_added / totalLoc) * 100 : 100

  return (
    <div className="contrib-card group">
      {/* Header section */}
      <div className="contrib-card-header">
        <div className="flex items-center gap-3">
          <div className="contrib-avatar shadow-lg" style={{ background: gradient }}>
            {initials}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-lg text-white m-0">
                {member.display_name}
              </h3>
              <span className="contrib-role-badge">
                {member.primary_role}
              </span>
              {member.github_username && (
                <a
                  href={`https://github.com/${member.github_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="contrib-github-btn"
                  title={`View @${member.github_username} on GitHub`}
                >
                  <GitBranch size={12} className="text-cyan-400" />
                  <span>@{member.github_username}</span>
                  <ExternalLink size={10} className="text-gray-500" />
                </a>
              )}
            </div>
            <div className="text-xs text-gray-400 font-mono mt-1">
              {member.canonical_email}
            </div>
          </div>
        </div>

        {/* Stats highlight pill */}
        <div className="contrib-card-stats">
          <div className="font-bold text-sm text-white flex items-center gap-1.5 justify-start sm:justify-end">
            <GitCommit size={14} className="text-cyan-400" />
            <span>{member.commits} commits ({member.commits_percentage}%)</span>
          </div>
          <div className="flex items-center gap-2 text-xs justify-start sm:justify-end">
            <span className="text-emerald-400 font-semibold">+{member.lines_added.toLocaleString()} LOC</span>
            <span className="text-gray-400">({member.lines_added_percentage}%)</span>
          </div>
        </div>
      </div>

      {/* Progress Bars & Code Churn */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs font-mono">
          <span className="text-gray-400">Commit Share</span>
          <span className="text-gray-300 font-semibold">{member.commits_percentage}%</span>
        </div>
        
        <div className="contrib-progress-bg">
          <div
            className="contrib-progress-fill"
            style={{ width: `${Math.max(member.commits_percentage, 2)}%`, background: gradient }}
          />
        </div>

        <div className="flex items-center justify-between text-[11px] text-gray-400 font-mono pt-0.5">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            <span>Added ({addedRatio.toFixed(1)}%)</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
            <span>Deleted ({(100 - addedRatio).toFixed(1)}%)</span>
          </div>
        </div>
      </div>

      {/* Deliverables section */}
      <div className="contrib-deliverables-box">
        <div className="text-xs font-bold text-gray-300 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 size={13} className="text-emerald-400" /> Key Features & Deliverables:
          </span>
          <span className="text-[11px] text-gray-400 font-normal flex items-center gap-1">
            <Sparkles size={11} className="text-amber-400" />
            {member.deliverables.length} item{member.deliverables.length !== 1 ? 's' : ''}
          </span>
        </div>
        <ul className="contrib-deliverables-list">
          {member.deliverables.map((item, idx) => (
            <li key={idx} className="contrib-deliverable-chip">
              <span className="text-cyan-400 font-bold">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
