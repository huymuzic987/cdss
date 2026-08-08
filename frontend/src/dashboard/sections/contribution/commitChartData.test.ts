import { describe, expect, it } from 'vitest'
import type { ContributorMetric } from '../../../api/types'
import {
  buildCommitTypeData,
  buildCommitVelocityData,
  classifyCommitType,
} from './commitChartData'

function contributor(memberKey: string, displayName: string, commits: number): ContributorMetric {
  return {
    member_key: memberKey,
    display_name: displayName,
    canonical_email: `${memberKey}@example.com`,
    github_username: memberKey,
    commits,
    commits_percentage: 0,
    lines_added: 0,
    lines_added_percentage: 0,
    lines_deleted: 0,
    total_loc_changes: 0,
    total_loc_percentage: 0,
    primary_role: 'Contributor',
    deliverables: [],
  }
}

describe('commit chart data', () => {
  it('classifies supported prefixes and treats unknown subjects as maintenance', () => {
    expect([
      classifyCommitType('feat(ui): add chart'),
      classifyCommitType('[Fix]: repair chart'),
      classifyCommitType('bugfix: repair parser'),
      classifyCommitType('refactor: split helper'),
      classifyCommitType('docs: explain chart'),
    ]).toEqual(['Feature', 'Fix', 'Fix', 'Refactor', 'Maintenance'])
  })

  it('counts real commit types by canonical contributor key without fallback values', () => {
    const contributors = [
      contributor('huy', 'Huy', 4),
      contributor('quang_minh', 'Quang Minh', 1),
      contributor('no_history', 'No History', 10),
    ]
    const commits = [
      { hash: '1', author: 'Huy', message: 'feat: add chart', timestamp: 4, member_keys: ['huy'] },
      { hash: '2', author: 'Huy', message: '[Fix]: repair chart', timestamp: 3, member_keys: ['huy', 'quang_minh'] },
      { hash: '3', author: 'Huy', message: 'refactor: split helper', timestamp: 2, member_keys: ['huy'] },
      { hash: '4', author: 'Huy', message: 'docs: explain chart', timestamp: 1, member_keys: ['huy'] },
    ]

    expect(buildCommitTypeData(contributors, commits)).toEqual([
      { name: 'Huy', Feature: 1, Fix: 1, Refactor: 1, Maintenance: 1 },
      { name: 'Quang Minh', Feature: 0, Fix: 1, Refactor: 0, Maintenance: 0 },
      { name: 'No History', Feature: 0, Fix: 0, Refactor: 0, Maintenance: 0 },
    ])
  })

  it('groups commits by UTC date and accumulates from zero in chronological order', () => {
    const commits = [
      { hash: '3', author: 'Huy', message: 'fix: third', timestamp: Date.parse('2026-06-29T08:00:00Z') / 1000, member_keys: ['huy'] },
      { hash: '1', author: 'Huy', message: 'feat: first', timestamp: Date.parse('2026-06-28T01:00:00Z') / 1000, member_keys: ['huy'] },
      { hash: '2', author: 'Huy', message: 'docs: second', timestamp: Date.parse('2026-06-28T23:00:00Z') / 1000, member_keys: ['huy'] },
    ]

    expect(buildCommitVelocityData(commits)).toEqual([
      { date: 'Jun 28, 2026', commits: 2, cumulative: 2 },
      { date: 'Jun 29, 2026', commits: 1, cumulative: 3 },
    ])
  })
})
