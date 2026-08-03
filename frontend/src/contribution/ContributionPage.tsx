import { ContributionSection } from '../dashboard/sections/ContributionSection'
import './contribution.css'

export function ContributionPage() {
  return (
    <div className="contrib-page">
      {/* Hero Header Banner */}
      <div className="contrib-hero">
        <div className="flex-1 min-w-0 flex flex-col gap-2 z-10">
          <h1 className="contrib-hero-title">
            Team Contribution & Deliverables Dashboard
          </h1>

          <p className="contrib-hero-subtitle">
            Automated git commit analysis tracking author contributions, LOC insertions, deletions, project deliverables, and cross-member collaboration domains in real-time.
          </p>
        </div>
      </div>

      {/* Main Section */}
      <ContributionSection />
    </div>
  )
}
