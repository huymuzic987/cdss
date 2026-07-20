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

  // Manual step-through mode: the full trace is fetched up front, but only
  // revealed one node_entered entry at a time, on each canvas click.
  const [manualMode, setManualMode] = useState(false)
  const [manualStepIndex, setManualStepIndex] = useState(0)
  const manualEntriesRef = useRef<TraversalTraceEntry[]>([])
  const manualFinalRef = useRef<{ result: EvaluationResponse | null; partial: ApiErrorResponse | null }>({
    result: null,
    partial: null,
  })

  // Generation token: each start/reset bumps this, and every in-flight call
  // captures its own id so a stale call can never be "un-cancelled" by a
  // later call resetting a shared flag.
  const runIdRef = useRef(0)

  // Shared: fire /evaluate, resolve the trace log, and preload every graph
  // the trace touches. Returns null (after setting error state) on hard failure.
  const runEvaluation = useCallback(
    async (
      runId: number,
      startTreeKey: string,
      input: JsonObject,
    ): Promise<{ result: EvaluationResponse | null; partial: ApiErrorResponse | null; traceLog: TraversalTraceEntry[] } | null> => {
      await ensureGraph(startTreeKey)
      if (runIdRef.current !== runId) return null
      setActiveTreeKey(startTreeKey)

      const { result, partial, error: evalError } = await evaluateTree({ start_tree_key: startTreeKey, input })
      if (runIdRef.current !== runId) return null

      if (evalError) {
        setError(evalError.message)
        setTraversalState('idle')
        return null
      }

      const traceLog: TraversalTraceEntry[] =
        result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []

      const uniqueTreeKeys = Array.from(new Set(traceLog.map((entry) => entry.tree_key)))
      await Promise.all(uniqueTreeKeys.map((key) => ensureGraph(key)))
      if (runIdRef.current !== runId) return null

      return { result, partial, traceLog }
    },
    [ensureGraph, setActiveTreeKey, setError],
  )

  const finish = useCallback(
    (result: EvaluationResponse | null, partial: ApiErrorResponse | null) => {
      setTraversalState('done')
      setModalResult(result)
      setModalPartial(partial)
      setShowModal(true)
    },
    [],
  )

  const handleStartTraversal = useCallback(
    async (startTreeKey: string, input: JsonObject): Promise<void> => {
      const runId = ++runIdRef.current
      setTraversalState('running')
      setHighlightedNodeKeys({})
      setActiveNodeKey(null)
      setActiveTraversalTreeKey(startTreeKey)
      setError(null)
      setShowModal(false)
      setManualMode(false)

      const evaluation = await runEvaluation(runId, startTreeKey, input)
      if (!evaluation) return
      const { result, partial, traceLog } = evaluation

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

      // Find the last entered node (walk backwards, no array copy)
      let lastEntry: TraversalTraceEntry | undefined
      for (let i = traceLog.length - 1; i >= 0; i--) {
        if (traceLog[i].event === 'node_entered') {
          lastEntry = traceLog[i]
          break
        }
      }
      if (lastEntry) {
        setActiveTraversalTreeKey(lastEntry.tree_key)
        setActiveTreeKey(lastEntry.tree_key)
        setActiveNodeKey(lastEntry.node_key)
        setFocusNodeKey(lastEntry.node_key)
      } else {
        setActiveNodeKey(null)
      }

      finish(result, partial)
    },
    [runEvaluation, setActiveTreeKey, setFocusNodeKey, setError, finish],
  )

  const handleStartManualTraversal = useCallback(
    async (startTreeKey: string, input: JsonObject): Promise<void> => {
      const runId = ++runIdRef.current
      setTraversalState('running')
      setHighlightedNodeKeys({})
      setActiveNodeKey(null)
      setActiveTraversalTreeKey(startTreeKey)
      setError(null)
      setShowModal(false)
      setManualMode(false)
      setManualStepIndex(0)

      const evaluation = await runEvaluation(runId, startTreeKey, input)
      if (!evaluation) return
      const { result, partial, traceLog } = evaluation

      const enteredEntries = traceLog.filter((entry) => entry.event === 'node_entered')
      manualEntriesRef.current = enteredEntries
      manualFinalRef.current = { result, partial }

      if (enteredEntries.length === 0) {
        finish(result, partial)
        return
      }

      setManualStepIndex(0)
      setManualMode(true)
    },
    [runEvaluation, finish, setError],
  )

  const handleManualStep = useCallback(() => {
    if (!manualMode) return
    const entries = manualEntriesRef.current
    if (manualStepIndex >= entries.length) return

    const entry = entries[manualStepIndex]

    setHighlightedNodeKeys((prev) => {
      const next = { ...prev }
      const existing = next[entry.tree_key] ? new Set(next[entry.tree_key]) : new Set<string>()
      existing.add(entry.node_key)
      next[entry.tree_key] = existing
      return next
    })
    setActiveTraversalTreeKey(entry.tree_key)
    setActiveTreeKey(entry.tree_key)
    setActiveNodeKey(entry.node_key)
    setFocusNodeKey(entry.node_key)

    const nextIndex = manualStepIndex + 1
    setManualStepIndex(nextIndex)

    if (nextIndex >= entries.length) {
      setManualMode(false)
      finish(manualFinalRef.current.result, manualFinalRef.current.partial)
    }
  }, [manualMode, manualStepIndex, setActiveTreeKey, setFocusNodeKey, finish])

  const handleReset = () => {
    runIdRef.current++
    setTraversalState('idle')
    setHighlightedNodeKeys({})
    setActiveNodeKey(null)
    setActiveTraversalTreeKey(null)
    setShowModal(false)
    setFocusNodeKey(null)
    setManualMode(false)
    setManualStepIndex(0)
    manualEntriesRef.current = []
  }

  const manualStepInfo =
    manualMode ? { current: manualStepIndex, total: manualEntriesRef.current.length } : null

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
    handleStartManualTraversal,
    handleManualStep,
    manualMode,
    manualStepInfo,
    handleReset,
  }
}
