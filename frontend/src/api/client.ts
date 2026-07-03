import type { ApiErrorResponse, TreeGraphResponse, TreeSummary } from './types'

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
