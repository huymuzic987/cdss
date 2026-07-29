import { useEvaluationRunner, type TraversalDependencies } from './traversal/useEvaluationRunner'
import { useManualTraversal } from './traversal/useManualTraversal'
import { useStandardTraversal } from './traversal/useStandardTraversal'
import { useTraversalStore } from './traversal/useTraversalStore'

export function useTraversal(dependencies: TraversalDependencies) {
  const store = useTraversalStore()
  const runEvaluation = useEvaluationRunner(store, dependencies)
  const handleStartTraversal = useStandardTraversal(store, dependencies, runEvaluation)
  const manual = useManualTraversal(store, dependencies, runEvaluation)

  const handlePregnancyPopupClose = useCallback(() => {
    setShowPregnancyPopup(false)
    setPregnancyPopupResult(null)
    const resume = pregnancyResumeRef.current
    pregnancyResumeRef.current = null
    if (!resume?.fullTraversal) return

    setHighlightedNodeKeys(buildHighlights(resume.trace))
    const lastEntry = [...resume.trace].reverse().find((entry) => entry.event === 'node_entered')
    if (lastEntry) {
      setActiveTraversalTreeKey(lastEntry.tree_key)
      setActiveTreeKey(lastEntry.tree_key)
      setActiveNodeKey(lastEntry.node_key)
      setFocusNodeKey(lastEntry.node_key)
    }
    finish(resume.result, resume.partial)
  }, [finish, setActiveTreeKey, setFocusNodeKey])

  const handleReset = () => {
    store.runIdRef.current += 1
    store.setTraversalState('idle')
    store.setHighlightedNodeKeys({})
    store.setActiveNodeKey(null)
    store.setActiveTraversalTreeKey(null)
    store.setShowModal(false)
    store.setShowDrugTolerancePopup(false)
    dependencies.setFocusNodeKey(null)
    store.setManualMode(false)
    store.setManualStepIndex(0)
    store.manualEntriesRef.current = []
  }

  return {
    traversalState: store.traversalState,
    highlightedNodeKeys: store.highlightedNodeKeys,
    activeNodeKey: store.activeNodeKey,
    activeTraversalTreeKey: store.activeTraversalTreeKey,
    modalResult: store.modalResult,
    modalPartial: store.modalPartial,
    showModal: store.showModal,
    setShowModal: store.setShowModal,
    showDrugTolerancePopup: store.showDrugTolerancePopup,
    handleStartTraversal,
    ...manual,
    manualMode: store.manualMode,
    manualStepInfo: store.manualMode
      ? { current: store.manualStepIndex, total: store.manualEntriesRef.current.length }
      : null,
    handleReset,
  }
}
