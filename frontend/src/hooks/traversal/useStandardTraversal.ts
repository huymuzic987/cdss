import { useCallback } from 'react'
import type { JsonObject } from '../../api/types'
import type { EmergencyScenarioFlags } from '../../panels/EmergencyScenarioCheckbox'
import { updateBundleClinicalFlag } from './bundleFlags'
import { drugToleranceIndex, hasDrugToleranceSelection, hasEmergencyScenarioSelection, highlightedByTree, isEmergencyCheckpoint, lastEntered } from './trace'
import type { EvaluationRunner, TraversalDependencies } from './useEvaluationRunner'
import type { TraversalStore } from './useTraversalStore'

export function useStandardTraversal(
  store: TraversalStore,
  dependencies: TraversalDependencies,
  runEvaluation: EvaluationRunner,
) {
  const start = useCallback(async (startTreeKey: string, input: JsonObject): Promise<void> => {
    const runId = ++store.runIdRef.current
    store.setTraversalState('running')
    store.setHighlightedNodeKeys({})
    store.setActiveNodeKey(null)
    store.setActiveTraversalTreeKey(startTreeKey)
    dependencies.setError(null)
    store.setShowModal(false)
    store.setCheckpointPending(false)
    store.setManualMode(false)

    const evaluation = await runEvaluation(runId, startTreeKey, input)
    if (!evaluation) return
    const { result, partial, traceLog } = evaluation
    const toleranceIndex = drugToleranceIndex(traceLog)
    const emergencyIndex = traceLog.findIndex((entry) => entry.event === 'node_entered'
      && isEmergencyCheckpoint(entry))

    if (toleranceIndex !== -1 && !hasDrugToleranceSelection(input)) {
      store.setCheckpointKind('resistant')
      store.setCheckpointPending(true)
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
    if (emergencyIndex !== -1 && !hasEmergencyScenarioSelection(input)) {
      store.setCheckpointKind('emergency')
      store.setCheckpointPending(true)
      store.manualStartTreeKeyRef.current = startTreeKey
      store.manualInputRef.current = { ...input }
      store.setHighlightedNodeKeys(highlightedByTree(traceLog.slice(0, emergencyIndex + 1)))
      const entry = traceLog[emergencyIndex]
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

  const confirmEmergency = useCallback(async (flags: EmergencyScenarioFlags) => {
    let input = store.manualInputRef.current
    for (const [key, value] of Object.entries(flags)) input = updateBundleClinicalFlag(input, key, value)
    const evaluation = await runEvaluation(++store.runIdRef.current, store.manualStartTreeKeyRef.current, input)
    if (!evaluation) return
    store.manualInputRef.current = input
    store.setCheckpointPending(false)
    store.setShowDrugTolerancePopup(false)
    store.setHighlightedNodeKeys(highlightedByTree(evaluation.traceLog))
    const lastEntry = lastEntered(evaluation.traceLog)
    if (lastEntry) {
      store.setActiveTraversalTreeKey(lastEntry.tree_key)
      dependencies.setActiveTreeKey(lastEntry.tree_key)
      store.setActiveNodeKey(lastEntry.node_key)
      dependencies.setFocusNodeKey(lastEntry.node_key)
    }
    store.finish(evaluation.result, evaluation.partial)
  }, [dependencies, runEvaluation, store])

  return { start, confirmEmergency }
}
