import { useCallback } from 'react'
import { evaluateFollowUp, evaluateTree } from '../../api/client'
import type { ApiErrorResponse, EvaluationResponse, JsonObject, TraversalTraceEntry, TreeGraphResponse } from '../../api/types'
import type { TraversalStore } from './useTraversalStore'

const FOLLOW_UP_START_TREE_KEY = 'treatment-threshold-and-bp-target'

export interface TraversalDependencies {
  ensureGraph: (treeKey: string) => Promise<TreeGraphResponse | null>
  setActiveTreeKey: (treeKey: string) => void
  setFocusNodeKey: (nodeKey: string | null) => void
  setError: (error: string | null) => void
}

export interface EvaluationRun {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  traceLog: TraversalTraceEntry[]
}

export function useEvaluationRunner(store: TraversalStore, dependencies: TraversalDependencies) {
  return useCallback(async (
    runId: number,
    startTreeKey: string,
    input: JsonObject,
  ): Promise<EvaluationRun | null> => {
    await dependencies.ensureGraph(startTreeKey)
    if (store.runIdRef.current !== runId) return null
    dependencies.setActiveTreeKey(startTreeKey)

    const { result, partial, error } = await (
      startTreeKey === FOLLOW_UP_START_TREE_KEY ? evaluateFollowUp(input) : evaluateTree(input)
    )
    if (store.runIdRef.current !== runId) return null
    if (error) {
      dependencies.setError(error.message)
      store.setTraversalState('idle')
      return null
    }

    const traceLog = result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []
    await Promise.all(Array.from(new Set(traceLog.map((entry) => entry.tree_key))).map(dependencies.ensureGraph))
    if (store.runIdRef.current !== runId) return null
    return { result, partial, traceLog }
  }, [dependencies, store])
}

export type EvaluationRunner = ReturnType<typeof useEvaluationRunner>
