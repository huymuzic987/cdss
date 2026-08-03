import { Activity, ShieldCheck, Sparkles } from 'lucide-react'
import { ContributionSection } from '../dashboard/sections/ContributionSection'
import './contribution.css'

export function ContributionPage() {
  return (
    <div className="contrib-page">
      {/* Hero Header Banner */}
      <div className="contrib-hero">
        <div className="space-y-2">
          <div className="contrib-hero-tag">
            <Sparkles size={14} />
            <span>Self-Hosted Git Analytics</span>
          </div>

          <h1 className="contrib-hero-title">
            Team Contribution & Deliverables Dashboard
          </h1>

          <p className="contrib-hero-subtitle">
            Automated git commit analysis tracking author contributions, LOC insertions, deletions, project deliverables, and cross-member collaboration domains in real-time.
          </p>
        </div>

        {/* Quick status badge */}
        <div className="contrib-hero-status">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Activity size={20} />
          </div>
          <div className="text-xs font-mono">
            <div className="text-white font-bold flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-emerald-400" />
              <span>Verified Git Tree</span>
            </div>
            <div className="text-gray-400 text-[11px] mt-0.5">Live Repository Engine</div>
          </div>
        </div>
      </div>

      {/* Main Section */}
      <ContributionSection />
    </div>
  )
}
