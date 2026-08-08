import type {
  ApiErrorResponse,
  ContributionResponse,
  DashboardFilters,
  DashboardSummaryResponse,
  EvaluationResponse,
  ImportResult,
  PatientDetailResponse,
  PatientListResponse,
  PatientSearchParams,
  TreeGraphResponse,
  TreeLayoutRequest,
  TreeLayoutResponse,
  TreeSummary,
  MedicineCatalogResponse,
  RegimenDecisionCreateRequest,
  RegimenDecisionResponse,
} from './types'
import type { JsonObject } from './types'

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

async function postJson<T>(path: string, payload?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    ...(payload === undefined ? {} : {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  })
  if (!response.ok) {
    const body = (await response.json()) as ApiErrorResponse
    throw new Error(body.message ?? `Request to ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}

async function putJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const body = (await response.json()) as ApiErrorResponse
    throw new Error(body.message ?? `Request to ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}

async function deleteRequest(path: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, { method: 'DELETE' })
  if (!response.ok && response.status !== 404) {
    const body = (await response.json()) as ApiErrorResponse
    throw new Error(body.message ?? `Request to ${path} failed with ${response.status}`)
  }
}

function buildQuery(params: object): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value))
    }
  }
  const queryString = searchParams.toString()
  return queryString ? `?${queryString}` : ''
}



export function fetchTrees(): Promise<TreeSummary[]> {
  return getJson<TreeSummary[]>('/trees')
}

export function fetchTreeGraph(treeKey: string): Promise<TreeGraphResponse> {
  return getJson<TreeGraphResponse>(`/trees/${encodeURIComponent(treeKey)}/graph`)
}

export function fetchTreeLayout(treeKey: string): Promise<TreeLayoutResponse> {
  return getJson<TreeLayoutResponse>(`/trees/${encodeURIComponent(treeKey)}/layout`)
}

export function saveTreeLayout(treeKey: string, layout: TreeLayoutRequest): Promise<TreeLayoutResponse> {
  return putJson<TreeLayoutResponse>(`/trees/${encodeURIComponent(treeKey)}/layout`, layout)
}

export function resetTreeLayout(treeKey: string): Promise<void> {
  return deleteRequest(`/trees/${encodeURIComponent(treeKey)}/layout`)
}

export function fetchMedicineCatalog(): Promise<MedicineCatalogResponse> {
  return getJson<MedicineCatalogResponse>('/medicines/catalog')
}

export function saveRegimenDecision(
  payload: RegimenDecisionCreateRequest,
): Promise<RegimenDecisionResponse> {
  return postJson<RegimenDecisionResponse>('/regimen-decisions', payload)
}

export interface EvaluationOutcome {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  error: ApiErrorResponse | null
}

export async function evaluateTree(bundle: JsonObject): Promise<EvaluationOutcome> {
  const response = await fetch(`${API_BASE_URL}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bundle),
  })
  const body = (await response.json()) as unknown
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

/** Known-stage medication follow-up: skips previous-visit inference. */
export async function evaluateFollowUp(bundle: JsonObject): Promise<EvaluationOutcome> {
  const response = await fetch(`${API_BASE_URL}/evaluate/follow-up`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bundle),
  })
  const body = (await response.json()) as unknown
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

export function fetchDashboardSummary(filters: DashboardFilters): Promise<DashboardSummaryResponse> {
  return getJson<DashboardSummaryResponse>(`/dashboard/summary${buildQuery(filters)}`)
}

export function fetchPatients(params: PatientSearchParams): Promise<PatientListResponse> {
  return getJson<PatientListResponse>(`/dashboard/patients${buildQuery(params)}`)
}

export function fetchPatientDetail(fhirId: string): Promise<PatientDetailResponse> {
  return getJson<PatientDetailResponse>(`/dashboard/patients/${encodeURIComponent(fhirId)}`)
}

export function seedDashboardData(source: 'preset' | 'synthetic' | 'real_test_case'): Promise<ImportResult> {
  return postJson<ImportResult>(`/dashboard/seed?source=${source}`)
}

export function fetchContributionStats(scope: 'main' | 'all' = 'main'): Promise<ContributionResponse> {
  return getJson<ContributionResponse>(`/dashboard/contributions?scope=${scope}`)
}

export function fhirPatientExportUrl(filters: DashboardFilters): string {
  const query = buildQuery(filters)
  const separator = query ? '&' : '?'
  return `${API_BASE_URL}/fhir/Patient${query}${separator}limit=500`
}
