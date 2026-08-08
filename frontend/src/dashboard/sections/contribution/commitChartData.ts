import type { CommitHistoryItem, ContributorMetric } from '../../../api/types'

export type CommitType = 'Feature' | 'Fix' | 'Refactor' | 'Maintenance'

export interface CommitTypeDatum {
  name: string
  Feature: number
  Fix: number
  Refactor: number
  Maintenance: number
}

export interface CommitVelocityDatum {
  date: string
  commits: number
  cumulative: number
}

const COMMIT_PREFIX = /^\s*\[?(feat|feature|fix|bugfix|refactor)\]?(?:\([^)]*\))?(?=[:\s]|$)/i
const DATE_FORMATTER = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
})

export function classifyCommitType(message: string): CommitType {
  const prefix = message.match(COMMIT_PREFIX)?.[1]?.toLowerCase()
  if (prefix === 'feat' || prefix === 'feature') return 'Feature'
  if (prefix === 'fix' || prefix === 'bugfix') return 'Fix'
  if (prefix === 'refactor') return 'Refactor'
  return 'Maintenance'
}

export function buildCommitTypeData(
  contributors: ContributorMetric[],
  commits: CommitHistoryItem[],
): CommitTypeDatum[] {
  return contributors.map((contributor) => {
    const datum: CommitTypeDatum = {
      name: contributor.display_name,
      Feature: 0,
      Fix: 0,
      Refactor: 0,
      Maintenance: 0,
    }
    for (const commit of commits) {
      if (commit.member_keys.includes(contributor.member_key)) {
        datum[classifyCommitType(commit.message)] += 1
      }
    }
    return datum
  })
}

export function buildCommitVelocityData(
  commits: CommitHistoryItem[],
): CommitVelocityDatum[] {
  const countsByDate = new Map<string, number>()
  for (const commit of commits) {
    if (!Number.isFinite(commit.timestamp)) continue
    const dateKey = new Date(commit.timestamp * 1000).toISOString().slice(0, 10)
    countsByDate.set(dateKey, (countsByDate.get(dateKey) ?? 0) + 1)
  }

  let cumulative = 0
  return [...countsByDate.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([dateKey, count]) => {
      cumulative += count
      return {
        date: DATE_FORMATTER.format(new Date(`${dateKey}T00:00:00Z`)),
        commits: count,
        cumulative,
      }
    })
}
