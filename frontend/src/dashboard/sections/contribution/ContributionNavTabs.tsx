import { Flame, GitCommit, GitMerge, LayoutGrid, PieChart as PieChartIcon } from 'lucide-react'

export type TabOption = 'all' | 'charts' | 'contributors' | 'matrix' | 'commits'

interface ContributionNavTabsProps {
  activeTab: TabOption
  setActiveTab: (tab: TabOption) => void
}

export function ContributionNavTabs({ activeTab, setActiveTab }: ContributionNavTabsProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
      <div className="contrib-tabs">
        <button
          type="button"
          onClick={() => setActiveTab('all')}
          className={`contrib-tab-btn ${activeTab === 'all' ? 'active' : ''}`}
        >
          <LayoutGrid size={13} /> All Views
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('charts')}
          className={`contrib-tab-btn ${activeTab === 'charts' ? 'active' : ''}`}
        >
          <PieChartIcon size={13} /> Analytics Charts
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('contributors')}
          className={`contrib-tab-btn ${activeTab === 'contributors' ? 'active' : ''}`}
        >
          <Flame size={13} /> Contributors
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('matrix')}
          className={`contrib-tab-btn ${activeTab === 'matrix' ? 'active' : ''}`}
        >
          <GitMerge size={13} /> Matrix
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('commits')}
          className={`contrib-tab-btn ${activeTab === 'commits' ? 'active' : ''}`}
        >
          <GitCommit size={13} /> Timeline
        </button>
      </div>
    </div>
  )
}
