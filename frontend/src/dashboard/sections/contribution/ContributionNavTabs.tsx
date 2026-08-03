import { Flame, GitCommit, GitMerge, LayoutGrid, PieChart as PieChartIcon } from 'lucide-react'

export type TabOption = 'all' | 'charts' | 'contributors' | 'matrix' | 'commits'

interface ContributionNavTabsProps {
  activeTab: TabOption
  setActiveTab: (tab: TabOption) => void
  contributorsCount?: number
  commitsCount?: number
  matrixCount?: number
}

export function ContributionNavTabs({
  activeTab,
  setActiveTab,
  contributorsCount,
  commitsCount,
  matrixCount,
}: ContributionNavTabsProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
      <div className="contrib-tabs">
        <button
          type="button"
          onClick={() => setActiveTab('all')}
          className={`contrib-tab-btn ${activeTab === 'all' ? 'active' : ''}`}
        >
          <LayoutGrid size={13} className={activeTab === 'all' ? 'text-cyan-400' : ''} />
          <span>All Views</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('charts')}
          className={`contrib-tab-btn ${activeTab === 'charts' ? 'active' : ''}`}
        >
          <PieChartIcon size={13} className={activeTab === 'charts' ? 'text-emerald-400' : ''} />
          <span>Analytics Charts</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('contributors')}
          className={`contrib-tab-btn ${activeTab === 'contributors' ? 'active' : ''}`}
        >
          <Flame size={13} className={activeTab === 'contributors' ? 'text-amber-400' : ''} />
          <span>Contributors</span>
          {contributorsCount !== undefined && (
            <span className="contrib-tab-count">{contributorsCount}</span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('matrix')}
          className={`contrib-tab-btn ${activeTab === 'matrix' ? 'active' : ''}`}
        >
          <GitMerge size={13} className={activeTab === 'matrix' ? 'text-purple-400' : ''} />
          <span>Matrix</span>
          {matrixCount !== undefined && (
            <span className="contrib-tab-count">{matrixCount}</span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('commits')}
          className={`contrib-tab-btn ${activeTab === 'commits' ? 'active' : ''}`}
        >
          <GitCommit size={13} className={activeTab === 'commits' ? 'text-blue-400' : ''} />
          <span>Timeline</span>
          {commitsCount !== undefined && (
            <span className="contrib-tab-count">{commitsCount}</span>
          )}
        </button>
      </div>
    </div>
  )
}
