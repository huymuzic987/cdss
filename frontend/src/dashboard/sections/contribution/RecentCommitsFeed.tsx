import { Check, Copy, GitCommit, Search, User } from 'lucide-react'
import { useState } from 'react'
import type { RecentCommitItem } from '../../../api/types'

function formatTimestamp(ts: number): string {
  if (!ts) return ''
  const date = new Date(ts * 1000)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function RecentCommitsFeed({ commits }: { commits: RecentCommitItem[] }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [copiedHash, setCopiedHash] = useState<string | null>(null)

  const filteredCommits = commits.filter(
    (c) =>
      c.hash.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.author.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleCopyHash = (hash: string) => {
    void navigator.clipboard.writeText(hash)
    setCopiedHash(hash)
    setTimeout(() => {
      setCopiedHash(null)
    }, 2000)
  }

  return (
    <div className="space-y-4">
      <div className="contrib-search-bar">
        <h3 className="text-base font-bold text-white flex items-center gap-2 m-0">
          <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <GitCommit size={18} />
          </div>
          <span>Recent Commits Activity</span>
        </h3>

        <div className="contrib-search-box">
          <Search size={14} className="contrib-search-icon" />
          <input
            type="text"
            placeholder="Search hash, author, message..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="contrib-search-input font-mono"
          />
        </div>
      </div>

      <div className="relative space-y-2.5 font-mono text-xs">
        {filteredCommits.length === 0 ? (
          <div className="p-6 text-center text-gray-400 bg-surface rounded-xl border border-white/10">
            No commits matching &quot;{searchTerm}&quot;
          </div>
        ) : (
          filteredCommits.map((c) => (
            <div key={c.hash} className="contrib-commit-item group">
              <div className="flex items-center gap-3 overflow-hidden">
                <button
                  type="button"
                  onClick={() => handleCopyHash(c.hash)}
                  className="contrib-hash-badge group/btn"
                  title="Click to copy commit hash"
                >
                  <span>{c.hash}</span>
                  {copiedHash === c.hash ? (
                    <Check size={12} className="text-emerald-400" />
                  ) : (
                    <Copy size={11} className="text-cyan-400/60 group-hover/btn:text-cyan-300" />
                  )}
                </button>

                <span className="text-gray-200 truncate font-sans text-xs group-hover:text-white transition-colors">
                  {c.message}
                </span>
              </div>

              <div className="flex items-center gap-3 shrink-0 text-xs font-sans">
                <span className="text-gray-400 flex items-center gap-1.5">
                  <User size={12} className="text-cyan-400" />
                  <span>by</span>
                  <strong className="text-cyan-300 font-semibold">{c.author}</strong>
                </span>

                {c.timestamp && (
                  <span className="text-[11px] text-gray-500 font-mono bg-black/30 px-2 py-0.5 rounded border border-white/5">
                    {formatTimestamp(c.timestamp)}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
