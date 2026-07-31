import { useCallback, useRef, useState } from 'react'
import type { ApiErrorResponse, EvaluationResponse, JsonObject, TraversalTraceEntry } from '../../api/types'

export type TraversalState = 'idle' | 'running' | 'done'

export function useTraversalStore() {
  const [traversalState, setTraversalState] = useState<TraversalState>('idle')
  const [highlightedNodeKeys, setHighlightedNodeKeys] = useState<Record<string, ReadonlySet<string>>>({})
  const [activeNodeKey, setActiveNodeKey] = useState<string | null>(null)
  const [activeTraversalTreeKey, setActiveTraversalTreeKey] = useState<string | null>(null)
  const [modalResult, setModalResult] = useState<EvaluationResponse | null>(null)
  const [modalPartial, setModalPartial] = useState<ApiErrorResponse | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [showDrugTolerancePopup, setShowDrugTolerancePopup] = useState(false)
  const [checkpointKind, setCheckpointKind] = useState<'resistant' | 'emergency'>('resistant')
  const [checkpointPending, setCheckpointPending] = useState(false)
  const [manualMode, setManualMode] = useState(false)
  const [manualStepIndex, setManualStepIndex] = useState(0)

  const manualEntriesRef = useRef<TraversalTraceEntry[]>([])
  const manualFinalRef = useRef<{ result: EvaluationResponse | null; partial: ApiErrorResponse | null }>({
    result: null,
    partial: null,
  })
  const manualStartTreeKeyRef = useRef('')
  const manualInputRef = useRef<JsonObject>({})
  const runIdRef = useRef(0)

  const finish = useCallback((result: EvaluationResponse | null, partial: ApiErrorResponse | null) => {
    setTraversalState('done')
    setModalResult(result)
    setModalPartial(partial)
    setShowModal(true)
  }, [])

  return {
    traversalState, setTraversalState,
    highlightedNodeKeys, setHighlightedNodeKeys,
    activeNodeKey, setActiveNodeKey,
    activeTraversalTreeKey, setActiveTraversalTreeKey,
    modalResult, modalPartial, showModal, setShowModal,
    showDrugTolerancePopup, setShowDrugTolerancePopup,
    checkpointKind, setCheckpointKind,
    checkpointPending, setCheckpointPending,
    manualMode, setManualMode,
    manualStepIndex, setManualStepIndex,
    manualEntriesRef, manualFinalRef, manualStartTreeKeyRef, manualInputRef, runIdRef,
    finish,
  }
}

export type TraversalStore = ReturnType<typeof useTraversalStore>
