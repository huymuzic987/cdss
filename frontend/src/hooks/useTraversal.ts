import { useCallback, useRef, useState } from 'react'
import { evaluateTree } from '../api/client'
import type {
  ApiErrorResponse,
  EvaluationResponse,
  JsonObject,
  TraversalTraceEntry,
  TreeGraphResponse,
} from '../api/types'

type TraversalState = 'idle' | 'running' | 'done'

interface UseTraversalOptions {
  ensureGraph: (treeKey: string) => Promise<TreeGraphResponse | null>
  setActiveTreeKey: (treeKey: string) => void
  setFocusNodeKey: (nodeKey: string | null) => void
  setError: (error: string | null) => void
}

export function useTraversal({ ensureGraph, setActiveTreeKey, setFocusNodeKey, setError }: UseTraversalOptions) {
  const [traversalState, setTraversalState] = useState<TraversalState>('idle')
  const [highlightedNodeKeys, setHighlightedNodeKeys] = useState<Record<string, ReadonlySet<string>>>({})
  const [activeNodeKey, setActiveNodeKey] = useState<string | null>(null)
  const [activeTraversalTreeKey, setActiveTraversalTreeKey] = useState<string | null>(null)

  const [modalResult, setModalResult] = useState<EvaluationResponse | null>(null)
  const [modalPartial, setModalPartial] = useState<ApiErrorResponse | null>(null)
  const [showModal, setShowModal] = useState(false)

  // Ref to abort in-flight animation
  const cancelRef = useRef(false)

  const handleStartTraversal = useCallback(
    async (startTreeKey: string, input: JsonObject): Promise<void> => {
      cancelRef.current = false
      setTraversalState('running')
      setHighlightedNodeKeys({})
      setActiveNodeKey(null)
      setActiveTraversalTreeKey(startTreeKey)
      setError(null)
      setShowModal(false)

      // Ensure starting graph is loaded & switch to its tab
      await ensureGraph(startTreeKey)
      if (cancelRef.current) return
      setActiveTreeKey(startTreeKey)

      // Call /evaluate
      const { result, partial, error: evalError } = await evaluateTree({ start_tree_key: startTreeKey, input })

      if (cancelRef.current) return

      if (evalError) {
        setError(evalError.message)
        setTraversalState('idle')
        return
      }

      const traceLog: TraversalTraceEntry[] =
        result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []

      // Preload all graphs in the path
      const uniqueTreeKeys = Array.from(new Set(traceLog.map((entry) => entry.tree_key)))
      await Promise.all(uniqueTreeKeys.map((key) => ensureGraph(key)))

      if (cancelRef.current) return

      // Group all entered nodes by tree key
      const enteredByTree: Record<string, Set<string>> = {}
      for (const entry of traceLog) {
        if (entry.event === 'node_entered') {
          if (!enteredByTree[entry.tree_key]) {
            enteredByTree[entry.tree_key] = new Set()
          }
          enteredByTree[entry.tree_key].add(entry.node_key)
        }
      }

      // Update the full highlighted set for all trees
      const newHighlights: Record<string, ReadonlySet<string>> = {}
      for (const [treeKey, nodeSet] of Object.entries(enteredByTree)) {
        newHighlights[treeKey] = nodeSet
      }
      setHighlightedNodeKeys(newHighlights)

      // Find the last entered node
      const lastEntry = [...traceLog].reverse().find((e) => e.event === 'node_entered')
      if (lastEntry) {
        setActiveTraversalTreeKey(lastEntry.tree_key)
        setActiveTreeKey(lastEntry.tree_key)
        setActiveNodeKey(lastEntry.node_key)
        setFocusNodeKey(lastEntry.node_key)
      } else {
        setActiveNodeKey(null)
      }

      setTraversalState('done')

      // Show result modal
      setModalResult(result)
      setModalPartial(partial)
      setShowModal(true)
    },
    [ensureGraph, setActiveTreeKey, setFocusNodeKey, setError],
  )

  const handleReset = () => {
    cancelRef.current = true
    setTraversalState('idle')
    setHighlightedNodeKeys({})
    setActiveNodeKey(null)
    setActiveTraversalTreeKey(null)
    setShowModal(false)
    setFocusNodeKey(null)
  }

  return {
    traversalState,
    highlightedNodeKeys,
    activeNodeKey,
    activeTraversalTreeKey,
    modalResult,
    modalPartial,
    showModal,
    setShowModal,
    handleStartTraversal,
    handleReset,
  }
}
