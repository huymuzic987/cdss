import { useCallback } from 'react'
import type { JsonObject } from '../../api/types'
import type { DrugToleranceResult } from '../../panels/DrugToleranceCheckbox'
import { updateBundleClinicalFlag } from './bundleFlags'
import { enteredEntries, hasDrugToleranceSelection, hasEmergencyScenarioSelection, highlightedByTree, isDrugToleranceEntry, isEmergencyCheckpoint, lastEntered, replaceRemainingEntries } from './trace'
import type { EmergencyScenarioFlags } from '../../panels/EmergencyScenarioCheckbox'
import type { EvaluationRunner, TraversalDependencies } from './useEvaluationRunner'
import type { TraversalStore } from './useTraversalStore'

export function useManualTraversal(
  store: TraversalStore,
  dependencies: TraversalDependencies,
  runEvaluation: EvaluationRunner,
) {
  const handleStartManualTraversal = useCallback(async (startTreeKey: string, input: JsonObject): Promise<void> => {
    const runId = ++store.runIdRef.current
    store.setTraversalState('running')
    store.setHighlightedNodeKeys({})
    store.setActiveNodeKey(null)
    store.setActiveTraversalTreeKey(startTreeKey)
    dependencies.setError(null)
    store.setShowModal(false)
    store.setCheckpointPending(false)
    store.setManualMode(false)
    store.setManualStepIndex(0)
    store.manualStartTreeKeyRef.current = startTreeKey
    store.manualInputRef.current = { ...input }

    const evaluation = await runEvaluation(runId, startTreeKey, input)
    if (!evaluation) return
    const entries = enteredEntries(evaluation.traceLog)
    store.manualEntriesRef.current = entries
    store.manualFinalRef.current = { result: evaluation.result, partial: evaluation.partial }
    if (entries.length === 0) {
      store.finish(evaluation.result, evaluation.partial)
      return
    }
    store.setManualStepIndex(0)
    store.setManualMode(true)
  }, [dependencies, runEvaluation, store])

  const handleEmergencyScenarioConfirm = useCallback(async (flags: EmergencyScenarioFlags) => {
    store.setShowDrugTolerancePopup(false)
    let input = store.manualInputRef.current
    for (const [key, value] of Object.entries(flags)) input = updateBundleClinicalFlag(input, key, value)
    store.manualInputRef.current = input
    const runId = ++store.runIdRef.current
    const evaluation = await runEvaluation(runId, store.manualStartTreeKeyRef.current, input)
    if (!evaluation) return
    store.setCheckpointPending(false)
    store.manualEntriesRef.current = replaceRemainingEntries(store.manualEntriesRef.current, store.manualStepIndex, evaluation.traceLog)
    store.manualFinalRef.current = { result: evaluation.result, partial: evaluation.partial }
    if (store.manualStepIndex >= store.manualEntriesRef.current.length) {
      store.setManualMode(false)
      store.finish(evaluation.result, evaluation.partial)
    }
  }, [runEvaluation, store])

  const handleManualStep = useCallback(() => {
    if (!store.manualMode || store.showDrugTolerancePopup) return
    const entry = store.manualEntriesRef.current[store.manualStepIndex]
    if (!entry) return
    store.setHighlightedNodeKeys((previous) => {
      const next = { ...previous }
      const keys = next[entry.tree_key] ? new Set(next[entry.tree_key]) : new Set<string>()
      keys.add(entry.node_key)
      next[entry.tree_key] = keys
      return next
    })
    store.setActiveTraversalTreeKey(entry.tree_key)
    dependencies.setActiveTreeKey(entry.tree_key)
    store.setActiveNodeKey(entry.node_key)
    dependencies.setFocusNodeKey(entry.node_key)

    const nextIndex = store.manualStepIndex + 1
    store.setManualStepIndex(nextIndex)
    if (isDrugToleranceEntry(entry) && !hasDrugToleranceSelection(store.manualInputRef.current)) {
      store.setCheckpointKind('resistant')
      store.setCheckpointPending(true)
      store.setShowDrugTolerancePopup(true)
      return
    }
    if (isEmergencyCheckpoint(entry) && !hasEmergencyScenarioSelection(store.manualInputRef.current)) {
      store.setCheckpointKind('emergency')
      store.setCheckpointPending(true)
      store.setShowDrugTolerancePopup(true)
      return
    }
    if (nextIndex >= store.manualEntriesRef.current.length) {
      store.setManualMode(false)
      store.finish(store.manualFinalRef.current.result, store.manualFinalRef.current.partial)
    }
  }, [dependencies, store])

  const handleDrugToleranceChange = useCallback((
    fieldKey: 'tolerates_mra' | 'tolerates_spironolactone',
    value: boolean,
  ) => {
    store.manualInputRef.current = updateBundleClinicalFlag(store.manualInputRef.current, fieldKey, value)
  }, [store])

  const handleDrugToleranceConfirm = useCallback(async (result: DrugToleranceResult) => {
    store.setShowDrugTolerancePopup(false)
    let input = updateBundleClinicalFlag(store.manualInputRef.current, 'tolerates_mra', result.tolerates_mra)
    input = updateBundleClinicalFlag(input, 'tolerates_spironolactone', result.tolerates_spironolactone)
    store.manualInputRef.current = input

    const runId = ++store.runIdRef.current
    const currentTreeKey = store.activeTraversalTreeKey
    const evaluation = await runEvaluation(runId, store.manualStartTreeKeyRef.current, input)
    if (!evaluation) return
    store.setCheckpointPending(false)
    if (currentTreeKey) dependencies.setActiveTreeKey(currentTreeKey)

    if (!store.manualMode) {
      store.setHighlightedNodeKeys(highlightedByTree(evaluation.traceLog))
      const lastEntry = lastEntered(evaluation.traceLog)
      if (lastEntry) {
        store.setActiveTraversalTreeKey(lastEntry.tree_key)
        dependencies.setActiveTreeKey(lastEntry.tree_key)
        store.setActiveNodeKey(lastEntry.node_key)
        dependencies.setFocusNodeKey(lastEntry.node_key)
      } else {
        store.setActiveNodeKey(null)
      }
      store.finish(evaluation.result, evaluation.partial)
      return
    }

    store.manualEntriesRef.current = replaceRemainingEntries(
      store.manualEntriesRef.current,
      store.manualStepIndex,
      evaluation.traceLog,
    )
    store.manualFinalRef.current = { result: evaluation.result, partial: evaluation.partial }
    if (store.manualStepIndex >= store.manualEntriesRef.current.length) {
      store.setManualMode(false)
      store.finish(evaluation.result, evaluation.partial)
    }
  }, [dependencies, runEvaluation, store])

  return {
    handleStartManualTraversal,
    handleManualStep,
    handleDrugToleranceChange,
    handleDrugToleranceConfirm,
    handleEmergencyScenarioConfirm,
    handleDrugToleranceCancel: () => store.setShowDrugTolerancePopup(false),
  }
}
