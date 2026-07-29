import type { TraversalTraceEntry } from '../../api/types'

const DRUG_TOLERANCE_NODE_KEYS = new Set(['T13_A_CHECK_MRA'])

export function enteredEntries(trace: TraversalTraceEntry[]): TraversalTraceEntry[] {
  return trace.filter((entry) => entry.event === 'node_entered')
}

export function highlightedByTree(trace: TraversalTraceEntry[]): Record<string, ReadonlySet<string>> {
  const grouped: Record<string, Set<string>> = {}
  for (const entry of enteredEntries(trace)) {
    if (!grouped[entry.tree_key]) grouped[entry.tree_key] = new Set()
    grouped[entry.tree_key].add(entry.node_key)
  }
  return grouped
}

export function lastEntered(trace: TraversalTraceEntry[]): TraversalTraceEntry | undefined {
  for (let index = trace.length - 1; index >= 0; index -= 1) {
    if (trace[index].event === 'node_entered') return trace[index]
  }
  return undefined
}

export function isDrugToleranceEntry(entry: TraversalTraceEntry): boolean {
  return (entry.tree_key === 'resistant-hypertension' || entry.tree_key === 'resistant_hypertension')
    && DRUG_TOLERANCE_NODE_KEYS.has(entry.node_key)
}

export function drugToleranceIndex(trace: TraversalTraceEntry[]): number {
  return trace.findIndex((entry) => entry.event === 'node_entered' && isDrugToleranceEntry(entry))
}

export function replaceRemainingEntries(
  previousEntries: TraversalTraceEntry[],
  shownCount: number,
  reevaluatedTrace: TraversalTraceEntry[],
): TraversalTraceEntry[] {
  const shown = previousEntries.slice(0, shownCount)
  const reevaluated = enteredEntries(reevaluatedTrace)
  let matched = 0
  for (let index = 0; index < reevaluated.length && matched < shown.length; index += 1) {
    if (reevaluated[index].node_key === shown[matched].node_key) matched += 1
  }
  return [...shown, ...reevaluated.slice(matched)]
}
