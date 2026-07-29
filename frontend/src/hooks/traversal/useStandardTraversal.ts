import { useCallback } from 'react'
import type { JsonObject } from '../../api/types'
import { drugToleranceIndex, highlightedByTree, lastEntered } from './trace'
import type { EvaluationRunner, TraversalDependencies } from './useEvaluationRunner'
import type { TraversalStore } from './useTraversalStore'

export function useStandardTraversal(
  store: TraversalStore,
  dependencies: TraversalDependencies,
  runEvaluation: EvaluationRunner,
) {
  return useCallback(async (startTreeKey: string, input: JsonObject): Promise<void> => {
    const runId = ++store.runIdRef.current
    store.setTraversalState('running')
    store.setHighlightedNodeKeys({})
    store.setActiveNodeKey(null)
    store.setActiveTraversalTreeKey(startTreeKey)
    dependencies.setError(null)
    store.setShowModal(false)
    store.setManualMode(false)

    const evaluation = await runEvaluation(runId, startTreeKey, input)
    if (!evaluation) return
    const { result, partial, traceLog } = evaluation
    const toleranceIndex = drugToleranceIndex(traceLog)

    if (toleranceIndex !== -1) {
      store.manualStartTreeKeyRef.current = startTreeKey
      store.manualInputRef.current = { ...input }
      store.setHighlightedNodeKeys(highlightedByTree(traceLog.slice(0, toleranceIndex + 1)))
      const entry = traceLog[toleranceIndex]
      store.setActiveTraversalTreeKey(entry.tree_key)
      dependencies.setActiveTreeKey(entry.tree_key)
      store.setActiveNodeKey(entry.node_key)
      dependencies.setFocusNodeKey(entry.node_key)
      store.setShowDrugTolerancePopup(true)
      return
    }

    store.setHighlightedNodeKeys(highlightedByTree(traceLog))
    const lastEntry = lastEntered(traceLog)
    if (lastEntry) {
      store.setActiveTraversalTreeKey(lastEntry.tree_key)
      dependencies.setActiveTreeKey(lastEntry.tree_key)
      store.setActiveNodeKey(lastEntry.node_key)
      dependencies.setFocusNodeKey(lastEntry.node_key)
    } else {
      store.setActiveNodeKey(null)
    }
    store.finish(result, partial)
  }, [dependencies, runEvaluation, store])
}
