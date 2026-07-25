import type {
  ApiErrorResponse,
  CdssUsageResponse,
  DashboardFilters,
  EfficacyResponse,
  EvaluationRequest,
  EvaluationResponse,
  FhirImportStatusResponse,
  ImportResult,
  NeedsAttentionResponse,
  OutcomesResponse,
  OverviewResponse,
  TreeGraphResponse,
  TreeSummary,
  VisitsResponse,
} from './types'

// Relative on purpose: the Vite dev server proxies these paths to the
// backend (see vite.config.ts), and the production nginx container does the
// same, so no environment-specific base URL is needed.
const API_BASE_URL = ''

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    const body = (await response.json()) as ApiErrorResponse
    throw new Error(body.message ?? `Request to ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}

async function postJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST' })
  if (!response.ok) {
    const body = (await response.json()) as ApiErrorResponse
    throw new Error(body.message ?? `Request to ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}

function buildQuery(params: DashboardFilters): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
  if (entries.length === 0) return ''
  return (
    '?' + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v as string)}`).join('&')
  )
}

export function fetchTrees(): Promise<TreeSummary[]> {
  return getJson<TreeSummary[]>('/trees')
}

export function fetchTreeGraph(treeKey: string): Promise<TreeGraphResponse> {
  return getJson<TreeGraphResponse>(`/trees/${encodeURIComponent(treeKey)}/graph`)
}

export async function evaluateTree(request: EvaluationRequest): Promise<{
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  error: ApiErrorResponse | null
}> {
  const response = await fetch(`${API_BASE_URL}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const body = (await response.json()) as EvaluationResponse | ApiErrorResponse
  if (response.ok) {
    return { result: body as EvaluationResponse, partial: null, error: null }
  }
  const err = body as ApiErrorResponse
  // 424 = LinkTargetNotFound — partial run state is available
  if (response.status === 424 && err.partial_run_state) {
    return { result: null, partial: err, error: null }
  }
  return { result: null, partial: null, error: err }
}

// ---- Dashboard ----

export function fetchDashboardOverview(filters: DashboardFilters): Promise<OverviewResponse> {
  return getJson<OverviewResponse>(`/dashboard/overview${buildQuery(filters)}`)
}

export function fetchDashboardVisits(filters: DashboardFilters): Promise<VisitsResponse> {
  return getJson<VisitsResponse>(`/dashboard/visits${buildQuery(filters)}`)
}

export function fetchDashboardOutcomes(filters: DashboardFilters): Promise<OutcomesResponse> {
  return getJson<OutcomesResponse>(`/dashboard/outcomes${buildQuery(filters)}`)
}

export function fetchDashboardCdssUsage(): Promise<CdssUsageResponse> {
  return getJson<CdssUsageResponse>('/dashboard/cdss-usage')
}

export function fetchDashboardEfficacy(): Promise<EfficacyResponse> {
  return getJson<EfficacyResponse>('/dashboard/efficacy')
}

export function fetchFhirImportStatus(): Promise<FhirImportStatusResponse> {
  return getJson<FhirImportStatusResponse>('/dashboard/fhir-import-status')
}

export function fetchNeedsAttention(): Promise<NeedsAttentionResponse> {
  return getJson<NeedsAttentionResponse>('/dashboard/needs-attention')
}

export function seedDashboardData(source: 'preset' | 'synthetic' | 'real_test_case'): Promise<ImportResult> {
  return postJson<ImportResult>(`/dashboard/seed?source=${source}`)
}

export function fhirPatientExportUrl(filters: DashboardFilters): string {
  const query = buildQuery(filters)
  const separator = query ? '&' : '?'
  return `${API_BASE_URL}/fhir/Patient${query}${separator}limit=500`
}
