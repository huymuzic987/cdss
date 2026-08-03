import { ArrowUpDown, Flame, GitCommit, RefreshCw, Search, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { fetchContributionStats } from '../../api/client'
import type { ContributionResponse } from '../../api/types'
import { ContributionCharts } from './contribution/ContributionCharts'
import { ContributionMetricsGrid } from './contribution/ContributionMetricsGrid'
import { ContributionNavTabs, type TabOption } from './contribution/ContributionNavTabs'
import { ContributorCard } from './contribution/ContributorCard'
import { OverlappingMatrixTable } from './contribution/OverlappingMatrixTable'
import { RecentCommitsFeed } from './contribution/RecentCommitsFeed'

type SortOption = 'commits' | 'lines_added' | 'total_loc'

export function ContributionSection() {
  const [scope, setScope] = useState<'main' | 'all'>('main')
  const [data, setData] = useState<ContributionResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [activeTab, setActiveTab] = useState<TabOption>('all')
  const [searchContributor, setSearchContributor] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('commits')

  const loadData = () => {
    setLoading(true)
    fetchContributionStats(scope)
      .then((res) => {
        setData(res)
        setLoading(false)
        setError(null)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err))
        setLoading(false)
      })
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchContributionStats(scope)
      .then((res) => {
        if (!cancelled) {
          setData(res)
          setLoading(false)
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err))
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [scope])

  const filteredContributors = useMemo(() => {
    if (!data?.contributors) return []
    return data.contributors
      .filter(
        (c) =>
          c.display_name.toLowerCase().includes(searchContributor.toLowerCase()) ||
          c.primary_role.toLowerCase().includes(searchContributor.toLowerCase()) ||
          c.deliverables.some((d) => d.toLowerCase().includes(searchContributor.toLowerCase()))
      )
      .sort((a, b) => {
        if (sortBy === 'lines_added') return b.lines_added - a.lines_added
        if (sortBy === 'total_loc') return b.total_loc_changes - a.total_loc_changes
        return b.commits - a.commits
      })
  }, [data?.contributors, searchContributor, sortBy])

  if (loading && !data) {
    return (
      <div className="p-8 text-center text-gray-400 animate-pulse flex items-center justify-center gap-2 bg-surface rounded-2xl border border-white/10">
        <GitCommit className="animate-spin text-cyan-400" size={20} />
        <span>Loading self-hosted team contribution metrics...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-4 bg-red-950/40 border border-red-500/30 text-red-300 rounded-xl text-sm">
        Failed to load contribution metrics: {error ?? 'Unknown error'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="contrib-section-header">
        <div>
          <h2 className="contrib-section-title">
            <Users className="text-cyan-400" size={22} />
            Team Member Contributions & Deliverables
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Real-time analytics parsed from self-hosted Git history on branch{' '}
            <code className="bg-cyan-950/80 px-1.5 py-0.5 rounded text-cyan-300 font-mono text-[11px] border border-cyan-800/40">
              {data.scope}
            </code>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="contrib-scope-switcher">
            <button
              type="button"
              className={`contrib-scope-btn ${scope === 'main' ? 'active' : ''}`}
              onClick={() => setScope('main')}
            >
              Production (main)
            </button>
            <button
              type="button"
              className={`contrib-scope-btn ${scope === 'all' ? 'active' : ''}`}
              onClick={() => setScope('all')}
            >
              All Branches
            </button>
          </div>
          <button
            type="button"
            onClick={loadData}
            title="Refresh statistics"
            className="contrib-btn-icon"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <ContributionMetricsGrid summary={data.summary} />
      <ContributionNavTabs activeTab={activeTab} setActiveTab={setActiveTab} />

      {(activeTab === 'all' || activeTab === 'charts') && <ContributionCharts contributors={data.contributors} />}

      {(activeTab === 'all' || activeTab === 'contributors') && (
        <div className="space-y-4">
          <div className="contrib-search-bar">
            <h3 className="text-base font-bold flex items-center gap-2 m-0">
              <Flame size={18} className="text-amber-400" /> Contributor Breakdown & Deliverables
            </h3>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <div className="contrib-search-box">
                <Search size={14} className="contrib-search-icon" />
                <input
                  type="text"
                  placeholder="Filter members..."
                  value={searchContributor}
                  onChange={(e) => setSearchContributor(e.target.value)}
                  className="contrib-search-input"
                />
              </div>

              <div className="flex items-center gap-1 bg-black/40 border border-white/10 px-2 py-1 rounded-lg text-xs">
                <ArrowUpDown size={12} className="text-gray-400" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="bg-transparent text-white focus:outline-none cursor-pointer text-xs"
                >
                  <option value="commits" className="bg-slate-900">Commits</option>
                  <option value="lines_added" className="bg-slate-900">Lines Added</option>
                  <option value="total_loc" className="bg-slate-900">Total LOC</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {filteredContributors.map((member, idx) => (
              <ContributorCard key={member.member_key} member={member} index={idx} />
            ))}
          </div>
        </div>
      )}

      {(activeTab === 'all' || activeTab === 'matrix') && <OverlappingMatrixTable matrix={data.overlapping_matrix} />}
      {(activeTab === 'all' || activeTab === 'commits') && <RecentCommitsFeed commits={data.recent_commits} />}
    </div>
  )
}
