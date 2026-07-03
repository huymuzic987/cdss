import type {
  ApiErrorResponse,
  EvaluationRequest,
  EvaluationResponse,
  TreeGraphResponse,
  TreeSummary,
} from './types'

const API_BASE_URL = 'http://localhost:8000'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    const body = (await response.json()) as ApiErrorResponse
    throw new Error(body.message ?? `Request to ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
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
