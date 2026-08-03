import { Activity, ShieldCheck, Sparkles } from 'lucide-react'
import { ContributionSection } from '../dashboard/sections/ContributionSection'
import './contribution.css'

export function ContributionPage() {
  return (
    <div className="contrib-page">
      {/* Hero Header Banner */}
      <div className="contrib-hero">
        <div className="flex-1 min-w-0 flex flex-col gap-2 z-10">
          <div className="contrib-hero-tag">
            <Sparkles size={14} className="text-amber-400 animate-pulse" />
            <span>Self-Hosted Git Analytics</span>
            <span className="contrib-hero-badge">v2.4 Pro</span>
          </div>

          <h1 className="contrib-hero-title">
            Team Contribution & Deliverables Dashboard
          </h1>

          <p className="contrib-hero-subtitle">
            Automated git commit analysis tracking author contributions, LOC insertions, deletions, project deliverables, and cross-member collaboration domains in real-time.
          </p>
        </div>

        {/* Quick status badge */}
        <div className="contrib-hero-status z-10">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-inner">
            <Activity size={20} className="animate-pulse" />
          </div>
          <div className="text-xs font-mono">
            <div className="text-white font-bold flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-emerald-400" />
              <span>Verified Git Tree</span>
            </div>
            <div className="text-gray-400 text-[11px] mt-0.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
              Live Repository Engine
            </div>
          </div>
        </div>
      </div>

      {/* Main Section */}
      <ContributionSection />
    </div>
  )
}
