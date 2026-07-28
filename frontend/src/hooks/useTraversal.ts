import { useCallback, useRef, useState } from 'react'
import { evaluateTree } from '../api/client'
import type {
  ApiErrorResponse,
  EvaluationResponse,
  JsonObject,
  TraversalTraceEntry,
  TreeGraphResponse,
} from '../api/types'
import type { DrugToleranceResult } from '../panels/DrugToleranceCheckbox'

type TraversalState = 'idle' | 'running' | 'done'

const DRUG_TOLERANCE_NODE_KEYS = new Set(['T13_A_CHECK_MRA'])

interface UseTraversalOptions {
  ensureGraph: (treeKey: string) => Promise<TreeGraphResponse | null>
  setActiveTreeKey: (treeKey: string) => void
  setFocusNodeKey: (nodeKey: string | null) => void
  setError: (error: string | null) => void
}

/** Update or insert one canonical local clinical-flag Condition. */
function updateBundleClinicalFlag(bundle: JsonObject, key: string, value: boolean): JsonObject {
  if (bundle['resourceType'] !== 'Bundle' || !Array.isArray(bundle['entry'])) {
    return { ...bundle, [key]: value }
  }

  const entries = [...bundle['entry']] as JsonObject[]
  const patient = entries
    .map((entry) => entry['resource'] as JsonObject | undefined)
    .find((resource) => resource?.['resourceType'] === 'Patient')
  const patientId = typeof patient?.['id'] === 'string' ? patient['id'] : 'simulated-patient'
  let foundCondition = false

  const updatedEntries: JsonObject[] = entries.map((e) => {
    const resource = e['resource'] as JsonObject | undefined
    const coding = resource?.['resourceType'] === 'Condition'
      ? ((resource['code'] as JsonObject | undefined)?.['coding'] as JsonObject[] | undefined)
      : undefined
    if (coding?.some((item) => item['system'] === 'http://cdss.local/fhir/CodeSystem/clinical-flag' && item['code'] === key)) {
      foundCondition = true
      return { ...e, resource: { ...resource, verificationStatus: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/condition-ver-status', code: value ? 'confirmed' : 'refuted' }] } } }
    }
    return e
  })

  if (!foundCondition) {
    updatedEntries.push({
      resource: {
        resourceType: 'Condition', id: `${patientId}-${key}`,
        subject: { reference: `Patient/${patientId}` },
        verificationStatus: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/condition-ver-status', code: value ? 'confirmed' : 'refuted' }] },
        code: { coding: [{ system: 'http://cdss.local/fhir/CodeSystem/clinical-flag', code: key }] },
      },
    })
  }

  return { ...bundle, entry: updatedEntries }
}

export function useTraversal({ ensureGraph, setActiveTreeKey, setFocusNodeKey, setError }: UseTraversalOptions) {
  const [traversalState, setTraversalState] = useState<TraversalState>('idle')
  const [highlightedNodeKeys, setHighlightedNodeKeys] = useState<Record<string, ReadonlySet<string>>>({})
  const [activeNodeKey, setActiveNodeKey] = useState<string | null>(null)
  const [activeTraversalTreeKey, setActiveTraversalTreeKey] = useState<string | null>(null)

  const [modalResult, setModalResult] = useState<EvaluationResponse | null>(null)
  const [modalPartial, setModalPartial] = useState<ApiErrorResponse | null>(null)
  const [showModal, setShowModal] = useState(false)

  // Drug tolerance popup — shown when manual step reaches T13_A_CHECK_MRA
  const [showDrugTolerancePopup, setShowDrugTolerancePopup] = useState(false)

  // Manual step-through mode: the full trace is fetched up front, but only
  // revealed one node_entered entry at a time, on each canvas click.
  const [manualMode, setManualMode] = useState(false)
  const [manualStepIndex, setManualStepIndex] = useState(0)
  const manualEntriesRef = useRef<TraversalTraceEntry[]>([])
  const manualFinalRef = useRef<{ result: EvaluationResponse | null; partial: ApiErrorResponse | null }>({
    result: null,
    partial: null,
  })

  // Store original traversal params so we can update tolerance variables and re-evaluate
  const manualStartTreeKeyRef = useRef<string>('')
  const manualInputRef = useRef<JsonObject>({})

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

      const { result, partial, error: evalError } = await evaluateTree(input)
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

      // If tree = resistant_hypertension and node = MRA tolerance -> show popup during full traverse
      const mraIdx = traceLog.findIndex(
        (entry) =>
          entry.event === 'node_entered' &&
          (entry.tree_key === 'resistant-hypertension') &&
          DRUG_TOLERANCE_NODE_KEYS.has(entry.node_key),
      )

      if (mraIdx !== -1) {
        manualStartTreeKeyRef.current = startTreeKey
        manualInputRef.current = { ...input }

        const pausedTrace = traceLog.slice(0, mraIdx + 1)
        const enteredByTree: Record<string, Set<string>> = {}
        for (const entry of pausedTrace) {
          if (entry.event === 'node_entered') {
            if (!enteredByTree[entry.tree_key]) enteredByTree[entry.tree_key] = new Set()
            enteredByTree[entry.tree_key].add(entry.node_key)
          }
        }
        const newHighlights: Record<string, ReadonlySet<string>> = {}
        for (const [treeKey, nodeSet] of Object.entries(enteredByTree)) {
          newHighlights[treeKey] = nodeSet
        }
        setHighlightedNodeKeys(newHighlights)

        const mraEntry = traceLog[mraIdx]
        setActiveTraversalTreeKey(mraEntry.tree_key)
        setActiveTreeKey(mraEntry.tree_key)
        setActiveNodeKey(mraEntry.node_key)
        setFocusNodeKey(mraEntry.node_key)

        setShowDrugTolerancePopup(true)
        return
      }

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

      manualStartTreeKeyRef.current = startTreeKey
      manualInputRef.current = { ...input }

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
    if (!manualMode || showDrugTolerancePopup) return
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

    // If we just stepped onto the MRA check node in resistant_hypertension, pause and show the popup
    const isResistantHypertension = entry.tree_key === 'resistant-hypertension' || entry.tree_key === 'resistant_hypertension'
    if (isResistantHypertension && DRUG_TOLERANCE_NODE_KEYS.has(entry.node_key)) {
      setShowDrugTolerancePopup(true)
      return
    }

    if (nextIndex >= entries.length) {
      setManualMode(false)
      finish(manualFinalRef.current.result, manualFinalRef.current.partial)
    }
  }, [manualMode, manualStepIndex, showDrugTolerancePopup, setActiveTreeKey, setFocusNodeKey, finish])

  const handleDrugToleranceChange = useCallback((fieldKey: 'tolerates_mra' | 'tolerates_spironolactone', value: boolean) => {
    manualInputRef.current = updateBundleClinicalFlag(manualInputRef.current, fieldKey, value)
  }, [])

  const handleDrugToleranceConfirm = useCallback(async (toleranceResult: DrugToleranceResult) => {
    setShowDrugTolerancePopup(false)

    // Ensure the FHIR input bundle has both boolean variables properly updated inside its Parameters resource
    let updatedInput = updateBundleClinicalFlag(manualInputRef.current, 'tolerates_mra', toleranceResult.tolerates_mra)
    updatedInput = updateBundleClinicalFlag(updatedInput, 'tolerates_spironolactone', toleranceResult.tolerates_spironolactone)
    manualInputRef.current = updatedInput

    const runId = ++runIdRef.current
    const currentTreeKey = activeTraversalTreeKey
    const evaluation = await runEvaluation(
      runId,
      manualStartTreeKeyRef.current,
      updatedInput,
    )
    if (!evaluation) return
    const { result, partial, traceLog } = evaluation

    // Keep viewing the current tree rather than jumping back to starting tree
    if (currentTreeKey) {
      setActiveTreeKey(currentTreeKey)
    }

    if (!manualMode) {
      // Complete full traverse mode normally with the re-evaluated trace
      const enteredByTree: Record<string, Set<string>> = {}
      for (const entry of traceLog) {
        if (entry.event === 'node_entered') {
          if (!enteredByTree[entry.tree_key]) enteredByTree[entry.tree_key] = new Set()
          enteredByTree[entry.tree_key].add(entry.node_key)
        }
      }
      const newHighlights: Record<string, ReadonlySet<string>> = {}
      for (const [treeKey, nodeSet] of Object.entries(enteredByTree)) {
        newHighlights[treeKey] = nodeSet
      }
      setHighlightedNodeKeys(newHighlights)

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
      return
    }

    const newEnteredEntries = traceLog.filter((entry) => entry.event === 'node_entered')

    const alreadyShown = manualEntriesRef.current.slice(0, manualStepIndex)
    let newStartIdx = 0
    for (let i = 0; i < newEnteredEntries.length && newStartIdx < alreadyShown.length; i++) {
      if (newEnteredEntries[i].node_key === alreadyShown[newStartIdx].node_key) {
        newStartIdx++
      }
    }
    const remainingNew = newEnteredEntries.slice(newStartIdx)
    manualEntriesRef.current = [...alreadyShown, ...remainingNew]
    manualFinalRef.current = { result, partial }

    if (manualStepIndex >= manualEntriesRef.current.length) {
      setManualMode(false)
      finish(result, partial)
    }
  }, [manualMode, manualStepIndex, finish, runEvaluation, activeTraversalTreeKey, setActiveTreeKey, setFocusNodeKey])

  const handleDrugToleranceCancel = useCallback(() => {
    setShowDrugTolerancePopup(false)
  }, [])

  const handleReset = () => {
    runIdRef.current++
    setTraversalState('idle')
    setHighlightedNodeKeys({})
    setActiveNodeKey(null)
    setActiveTraversalTreeKey(null)
    setShowModal(false)
    setShowDrugTolerancePopup(false)
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
    showDrugTolerancePopup,
    handleDrugToleranceConfirm,
    handleDrugToleranceCancel,
    handleDrugToleranceChange,
    handleStartTraversal,
    handleStartManualTraversal,
    handleManualStep,
    manualMode,
    manualStepInfo,
    handleReset,
  }
}
