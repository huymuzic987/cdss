import type { TreeGraphResponse } from '../api/types'

/** Minimal shape guard against a malformed backend response -- just enough to
 * avoid `graph.nodes.map(...)`-style crashes. Not a full schema validator. */
export function isValidTreeGraph(graph: TreeGraphResponse): boolean {
  return (
    !!graph &&
    !!graph.tree &&
    typeof graph.tree.tree_key === 'string' &&
    graph.tree.tree_key.length > 0 &&
    Array.isArray(graph.nodes) &&
    Array.isArray(graph.edges)
  )
}
