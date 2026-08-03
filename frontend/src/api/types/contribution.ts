// Contribution Types (mirrors src/cdss/api/schemas/dashboard.py)

export interface ContributorMetric {
  member_key: string
  display_name: string
  canonical_email: string
  github_username?: string | null
  commits: number
  commits_percentage: number
  lines_added: number
  lines_added_percentage: number
  lines_deleted: number
  total_loc_changes: number
  total_loc_percentage: number
  primary_role: string
  deliverables: string[]
}

export interface ContributionSummary {
  total_commits: number
  total_lines_added: number
  total_lines_deleted: number
  total_loc_changes: number
  active_contributors: number
}

export interface OverlappingTask {
  feature_area: string
  collaborators: string[]
  shared_deliverables: string
}

export interface RecentCommitItem {
  hash: string
  author: string
  message: string
  timestamp: number
}

export interface ContributionResponse {
  summary: ContributionSummary
  contributors: ContributorMetric[]
  overlapping_matrix: OverlappingTask[]
  recent_commits: RecentCommitItem[]
  scope: string
  updated_at: string
}
