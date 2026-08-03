import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as apiModule from '../../api/client'
import type { ContributionResponse } from '../../api/types'
import { ContributionSection } from './ContributionSection'

const MOCK_RESPONSE: ContributionResponse = {
  summary: {
    total_commits: 127,
    total_lines_added: 260204,
    total_lines_deleted: 72584,
    total_loc_changes: 332788,
    active_contributors: 5,
  },
  contributors: [
    {
      member_key: 'huy',
      display_name: 'Huy',
      canonical_email: 'huymusic987@gmail.com',
      github_username: 'huymuzic987',
      commits: 90,
      commits_percentage: 70.9,
      lines_added: 231269,
      lines_added_percentage: 88.9,
      lines_deleted: 69618,
      total_loc_changes: 300887,
      total_loc_percentage: 90.4,
      primary_role: 'Lead Architect & Full-Stack Engineer',
      deliverables: ['Core Decision Tree Traversal Walker Engine'],
    },
    {
      member_key: 'quang_minh',
      display_name: 'Quang Minh',
      canonical_email: 'phamlequangminh2411@gmail.com',
      github_username: 'Quangminh_24112005',
      commits: 31,
      commits_percentage: 24.4,
      lines_added: 28838,
      lines_added_percentage: 11.1,
      lines_deleted: 2897,
      total_loc_changes: 31735,
      total_loc_percentage: 9.5,
      primary_role: 'Full-Stack & Clinical Data Engineer',
      deliverables: ['Pregnancy & Postpartum Longitudinal Pathway Engine'],
    },
  ],
  overlapping_matrix: [
    {
      feature_area: 'Decision Trees 1–14 Authoring & Maintenance',
      collaborators: ['Khoa Dang', 'Quang Minh', 'Huy'],
      shared_deliverables: 'Khoa authored Trees 7,9,10,13; Quang Minh authored Trees 6,8,11,12,14.',
    },
  ],
  recent_commits: [
    {
      hash: '010d9c7',
      author: 'huymuzic987',
      message: 'refactor: remove legacy bp_target_reached boolean',
      timestamp: 1754104800,
    },
  ],
  scope: 'main',
  updated_at: '2026-08-02T12:00:00Z',
}

describe('ContributionSection Component', () => {
  it('renders contribution metrics and member list', async () => {
    vi.spyOn(apiModule, 'fetchContributionStats').mockResolvedValue(MOCK_RESPONSE)

    render(<ContributionSection />)

    expect(screen.getByText(/Loading self-hosted team contribution metrics/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Team Member Contributions & Deliverables')).toBeInTheDocument()
    })

    expect(screen.getAllByText('Huy')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Quang Minh')[0]).toBeInTheDocument()
    expect(screen.getByText('Lead Architect & Full-Stack Engineer')).toBeInTheDocument()
    expect(screen.getByText('Core Decision Tree Traversal Walker Engine')).toBeInTheDocument()
  })
})
