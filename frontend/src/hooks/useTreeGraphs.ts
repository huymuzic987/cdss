import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchTreeGraph, fetchTrees } from '../api/client'
import type { TreeGraphNode, TreeGraphResponse, TreeSummary } from '../api/types'

const TRAVERSAL_ORDER = [
  'hypertension-diagnosis',
  'risk-classification',
  'treatment-threshold-and-bp-target',
  'essential-treatment-strategy',
  'optimal-treatment-strategy',
]

export function useTreeGraphs() {
  const [trees, setTrees] = useState<TreeSummary[]>([])
  const [activeTreeKey, setActiveTreeKey] = useState<string | null>(null)
  const [graphCache, setGraphCache] = useState<Record<string, TreeGraphResponse>>({})
  const [focusNodeKey, setFocusNodeKey] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<TreeGraphNode | null>(null)
  const [error, setError] = useState<string | null>(null)

  // ---- Initial load ----
  useEffect(() => {
    fetchTrees()
      .then((summaries) => {
        const ordered = [...summaries].sort((a, b) => {
          const idxA = TRAVERSAL_ORDER.indexOf(a.tree_key)
          const idxB = TRAVERSAL_ORDER.indexOf(b.tree_key)
          const valA = idxA === -1 ? 999 : idxA
          const valB = idxB === -1 ? 999 : idxB
          return valA - valB
        })
        setTrees(ordered)
        setActiveTreeKey(ordered[0]?.tree_key ?? null)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  // ---- Lazy-load graph when switching tabs ----
  const inFlightRef = useRef<Set<string>>(new Set())
  useEffect(() => {
    if (!activeTreeKey || graphCache[activeTreeKey] || inFlightRef.current.has(activeTreeKey)) return
    inFlightRef.current.add(activeTreeKey)
    fetchTreeGraph(activeTreeKey)
      .then((graph) => setGraphCache((prev) => ({ ...prev, [activeTreeKey]: graph })))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => inFlightRef.current.delete(activeTreeKey))
  }, [activeTreeKey, graphCache])

  // ---- Ensure a tree graph is loaded (used during simulation) ----
  const ensureGraph = useCallback(
    async (treeKey: string): Promise<TreeGraphResponse | null> => {
      if (graphCache[treeKey]) return graphCache[treeKey]
      try {
        const graph = await fetchTreeGraph(treeKey)
        setGraphCache((prev) => ({ ...prev, [treeKey]: graph }))
        return graph
      } catch {
        return null
      }
    },
    [graphCache],
  )

  // ---- Jump-to-link (from node detail panel) ----
  const handleJumpToLink = useCallback(
    async (targetTreeKey: string, targetNodeKey: string | null) => {
      let targetGraph = graphCache[targetTreeKey]
      if (!targetGraph) {
        try {
          targetGraph = await fetchTreeGraph(targetTreeKey)
          setGraphCache((prev) => ({ ...prev, [targetTreeKey]: targetGraph }))
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err))
          return
        }
      }
      setActiveTreeKey(targetTreeKey)
      setFocusNodeKey(targetNodeKey ?? targetGraph.start_node_key)
    },
    [graphCache],
  )

  const handleSelectTab = (treeKey: string) => {
    setActiveTreeKey(treeKey)
    setFocusNodeKey(null)
    setSelectedNode(null)
  }

  const activeGraph = activeTreeKey ? graphCache[activeTreeKey] : undefined

  return {
    trees,
    activeTreeKey,
    setActiveTreeKey,
    graphCache,
    focusNodeKey,
    setFocusNodeKey,
    selectedNode,
    setSelectedNode,
    error,
    setError,
    activeGraph,
    ensureGraph,
    handleSelectTab,
    handleJumpToLink,
  }
}
