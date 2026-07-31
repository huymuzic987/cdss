import type {
  EvaluationResponse,
  ExecutedAction,
  JsonObject,
  JsonValue,
  TraversalTraceEntry,
  TreeGraphResponse,
} from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { confirmedText, formatEvaluation, uniqueFindings } from './criticalFindingFormat'
import { readableIdentifier } from './decisionPath'
import { deriveFollowUpAdvice } from './followUpAdvice'
import type { ClinicalUrgency, CriticalSummary, ImportantPathStep } from './criticalSummaryTypes'

export type {
  ClinicalUrgency, CriticalFinding, CriticalSummary, FollowUpAdvice, ImportantPathStep,
} from './criticalSummaryTypes'

interface SummaryInput {
  log: TraversalTraceEntry[]
  actions: ExecutedAction[]
  context: JsonObject
  graphs: Record<string, TreeGraphResponse>
  locale: ClinicalDecisionSupportLocale
  pregnancyFollowUp?: EvaluationResponse['pregnancy_follow_up']
}

const NONMATERIAL_OUTPUT = /MAINTAIN|CONTINUE_MONITOR|TARGET_ACHIEVED|BP_NOT_HIGH|NORMAL_BP/
const ROUTE_CHANGING = /EMERGEN|SEVERE|ECLAMP|HELLP|CRISIS|PULMONARY|ORGAN|TARGET|RISK|PREGNAN|POSTPARTUM|DIABET|KIDNEY|CKD|CORONARY|STROKE|HEART|FRAIL|PROTEIN|TOLERAN|CONTRAIND|AGE|FACILIT|RESOURCE|ADHER|BREASTFEED|CREATININE|POTASSIUM|EGFR|MEDICATION|REGIMEN|THROMBOL|AORTIC|NORMAL_BP|CLINIC_BP/
const ADMINISTRATIVE = /MEDICATION_FOLLOW_UP|FOLLOW_UP_VISIT|FOLLOW_UP_AFTER|INITIAL_REGIMEN|FOLLOW_UP_STAGE/
const MEDICATION_INFERENCE = /DRUG|MEDIC|THERAP|REGIMEN|ASPIRIN|LABETALOL|METHYLDOPA|NIFEDIPINE|NICARDIPINE|MAGNESIUM|COMBINATION/i
const IMMEDIATE_PREGNANCY = /ECLAMPSIA_CLASSIFICATION|HELLP_SYNDROME|TARGET_NOT_MET|BP_SEVERE|HYPERTENSIVE_CRISIS|PULMONARY_EDEMA|EMERGENCY_DELIVERY/
const ACTIVE_PREGNANCY_HTN = /GESTATIONAL_HTN|PREECLAMPSIA|PRE_EXISTING_HTN|CHRONIC_HTN|BP_HIGH|BP_SEVERE|IMMEDIATE_TARGET/

export function deriveCriticalSummary(input: SummaryInput): CriticalSummary {
  const entered = input.log.filter((entry) => entry.event === 'node_entered')
  const enteredTokens = entered.map((entry) => entry.node_key).join(' ').toUpperCase()
  const tokens = [
    ...entered.flatMap((entry) => [entry.tree_key, entry.node_key]),
    ...input.actions.flatMap((action) => [
      action.node_key, action.text_en, stringField(action.payload, 'action_type'),
    ]),
  ].join(' ').toUpperCase()
  const recordedRisk = nestedString(input.context, 'risk', 'level').toUpperCase()
  const risk = recordedRisk || (/HIGH_PREECLAMPSIA_RISK|ASPIRIN_PROPHYLAXIS/.test(tokens) ? 'HIGH' : '')
  const postpartum = tokens.includes('POSTPARTUM')
  const pregnancy = tokens.includes('PREGNAN') || postpartum
  const activePregnancyHypertension = pregnancy && ACTIVE_PREGNANCY_HTN.test(enteredTokens)
  const immediate = tokens.includes('HYPERTENSIVE-EMERGENCY')
    || (pregnancy && IMMEDIATE_PREGNANCY.test(tokens))
  const urgency: ClinicalUrgency = immediate
    ? 'immediate'
    : ['HIGH', 'VERY_HIGH'].includes(risk) || pregnancy
      ? 'high'
      : risk === 'MODERATE' ? 'moderate' : 'routine'
  const path = importantPath(input, entered)
  const direct = path.flatMap((step) => step.kind === 'trigger' && step.detail
    ? [{ id: step.id, label: step.label, value: step.detail, treeName: step.treeName }]
    : [])
  const patientStats = contextPatientFindings(input.context, input.locale)
  const fallback = path.flatMap((step) => ['urgent', 'classification'].includes(step.kind)
    && !MEDICATION_INFERENCE.test(`${step.label} ${step.detail ?? ''}`)
    ? [{
        id: step.id, label: step.label, value: step.detail || confirmedText(input.locale),
        treeName: step.treeName,
      }]
    : [])
  return {
    urgency,
    urgencyLabel: urgencyText(urgency, input.locale),
    findings: uniqueFindings([...patientStats, ...direct, ...fallback]).slice(0, 5),
    path,
    followUp: deriveFollowUpAdvice(
      input.actions,
      input.pregnancyFollowUp,
      { risk, pregnancy, postpartum, immediate, activePregnancyHypertension },
      input.locale,
    ),
  }
}

function contextPatientFindings(
  context: JsonObject, locale: ClinicalDecisionSupportLocale,
): CriticalSummary['findings'] {
  const diagnosis = object(context.diagnosis)
  const treatment = object(context.treatment)
  const risk = object(context.risk)
  const values: Array<[string, JsonValue | undefined, string]> = [
    ['Hypertension class', diagnosis?.hypertension_class, 'diagnosis'],
    ['Clinic BP', clinicBloodPressure(diagnosis), 'diagnosis'],
    ['Risk level', risk?.level, 'risk'],
    ['Treatment status', treatment?.status, 'treatment'],
  ]
  return values.flatMap(([label, value, group]) => {
    if (value === undefined || value === null || value === '') return []
    const shown = typeof value === 'string' ? readableIdentifier(value) : String(value)
    return [{ id: `patient:${group}:${label}`, label, value: shown, treeName: locale === 'vi' ? 'Thông tin bệnh nhân' : 'Patient profile' }]
  })
}

function clinicBloodPressure(diagnosis: JsonObject | null): string | undefined {
  const sbp = diagnosis?.current_clinic_sbp
  const dbp = diagnosis?.current_clinic_dbp
  if (typeof sbp !== 'number' && typeof dbp !== 'number') return undefined
  return `${typeof sbp === 'number' ? sbp : '—'} / ${typeof dbp === 'number' ? dbp : '—'} mmHg`
}

function importantPath(input: SummaryInput, entered: TraversalTraceEntry[]): ImportantPathStep[] {
  const accepted = new Map<string, TraversalTraceEntry>()
  for (const entry of input.log) {
    if (entry.event === 'candidate_evaluated' && entry.condition_result && entry.candidate_node_key) {
      accepted.set(`${entry.tree_key}:${entry.candidate_node_key}`, entry)
    }
  }
  const candidates = entered.flatMap((entry, index) => {
    const graph = input.graphs[entry.tree_key]
    const node = graph?.nodes.find((item) => item.node_key === entry.node_key)
    const executed = input.actions.find(
      (action) => action.tree_key === entry.tree_key && action.node_key === entry.node_key,
    )
    const token = `${entry.node_key} ${node?.text_en ?? executed?.text_en ?? ''}`.toUpperCase()
    const payload = node?.action_payload ?? executed?.payload
    const actionType = stringField(payload, 'action_type').toUpperCase()
    const meaningfulAction = Boolean(payload) && !NONMATERIAL_OUTPUT.test(`${token} ${actionType}`)
    const include = entry.node_type === 'CONDITION'
      ? ROUTE_CHANGING.test(token) && !ADMINISTRATIVE.test(token)
        && !/(?:^|[_-])(?:NO|NOT)(?:[_-])/.test(token)
      : entry.node_type === 'INFERENCE'
        ? entry.changed_context_paths.length > 0 && !/RESTORE|COPY|SET_CURRENT/.test(token)
        : ['ACTION', 'END'].includes(entry.node_type) && meaningfulAction
    if (!include) return []
    const match = accepted.get(`${entry.tree_key}:${entry.node_key}`)
    const urgent = /EMERGEN|ECLAMP|HELLP|CRISIS|SEVERE|TARGET_NOT/.test(token)
    const kind = urgent ? 'urgent'
      : entry.node_type === 'CONDITION' ? 'trigger'
        : entry.node_type === 'INFERENCE' ? 'classification' : 'treatment'
    return [{
      index,
      score: urgent ? 5 : kind === 'treatment' ? 4 : kind === 'classification' ? 3 : 2,
      step: {
        id: `${entry.tree_key}:${entry.node_key}`,
        label: localizedNodeText(
          node?.text_en ?? executed?.text_en, node?.text_vi ?? executed?.text_vi,
          entry.node_key, input.locale,
        ),
        treeName: localizedTreeName(graph, entry.tree_key, input.locale),
        detail: formatEvaluation(match?.evaluation_details),
        kind,
      } satisfies ImportantPathStep,
    }]
  })
  const selected = candidates.length <= 6 ? candidates
    : [...candidates].sort((a, b) => b.score - a.score || a.index - b.index).slice(0, 6)
  return selected.sort((a, b) => a.index - b.index).map(({ step }) => step)
}

function urgencyText(urgency: ClinicalUrgency, locale: ClinicalDecisionSupportLocale): string {
  const labels = {
    immediate: ['Immediate', 'Khẩn cấp'], high: ['High priority', 'Ưu tiên cao'],
    moderate: ['Moderate priority', 'Ưu tiên vừa'], routine: ['Routine', 'Thường quy'],
  }
  return labels[urgency][locale === 'vi' ? 1 : 0]
}

function localizedNodeText(
  en: string | undefined, vi: string | undefined, key: string, locale: ClinicalDecisionSupportLocale,
): string {
  return locale === 'vi' ? vi || en || readableIdentifier(key) : en || vi || readableIdentifier(key)
}

function localizedTreeName(
  graph: TreeGraphResponse | undefined, key: string, locale: ClinicalDecisionSupportLocale,
): string {
  if (!graph) return readableIdentifier(key)
  return locale === 'vi' ? graph.tree.name_vi || graph.tree.name_en : graph.tree.name_en || graph.tree.name_vi
}

function nestedString(root: JsonObject, parent: string, key: string): string {
  return stringField(object(root[parent]), key)
}

function object(value: JsonValue | undefined): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value : null
}

function stringField(value: JsonObject | null | undefined, key: string): string {
  return typeof value?.[key] === 'string' ? value[key] : ''
}
