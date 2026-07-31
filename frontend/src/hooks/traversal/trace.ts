import type { JsonObject, TraversalTraceEntry } from '../../api/types'

const DRUG_TOLERANCE_NODE_KEYS = new Set(['T13_A_CHECK_MRA'])
const EMERGENCY_CHECKPOINT = 'T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN'
const EMERGENCY_FLAGS = [
  'has_hypertensive_encephalopathy', 'has_acute_ischemic_stroke',
  'is_thrombolysis_candidate', 'has_acute_intracerebral_hemorrhage',
  'has_acute_coronary_syndrome', 'has_acute_cardiogenic_pulmonary_edema',
  'has_acute_aortic_syndrome', 'has_eclampsia_severe_preeclampsia_or_hellp',
  'has_tma_or_acute_kidney_injury',
]
const CLINICAL_FLAG_SYSTEM = 'http://cdss.local/fhir/CodeSystem/clinical-flag'

function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? value as Record<string, unknown> : null
}

function flagStatus(input: JsonObject, key: string): boolean | undefined {
  if (typeof input[key] === 'boolean') return input[key] as boolean
  const entries = Array.isArray(input.entry) ? input.entry : []
  for (const raw of entries) {
    const resource = object(object(raw)?.resource)
    if (resource?.resourceType !== 'Condition') continue
    const code = object(resource.code)
    const codings = Array.isArray(code?.coding) ? code.coding : []
    const matches = codings.some((item) => {
      const coding = object(item)
      return coding?.system === CLINICAL_FLAG_SYSTEM && coding.code === key
    })
    if (!matches) continue
    const verification = object(resource.verificationStatus)
    const statuses = Array.isArray(verification?.coding) ? verification.coding : []
    const status = statuses.map((item) => object(item)?.code).find((value) => value === 'confirmed' || value === 'refuted')
    if (status === 'confirmed') return true
    if (status === 'refuted') return false
  }
  return undefined
}

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

export function isEmergencyCheckpoint(entry: TraversalTraceEntry): boolean {
  return entry.tree_key === 'hypertensive-emergency' && entry.node_key === EMERGENCY_CHECKPOINT
}

export function hasEmergencyScenarioSelection(input: JsonObject): boolean {
  return EMERGENCY_FLAGS.some((key) => flagStatus(input, key) === true)
}

export function hasDrugToleranceSelection(input: JsonObject): boolean {
  return flagStatus(input, 'tolerates_mra') !== undefined
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
