import type { ActionOption } from '../clinicalDecisionSupportAdapter'
import type { JsonObject, JsonValue } from '../../api/types'
import type { CriticalSummary } from './criticalSummaryTypes'

const MEDICATION = /DRUG|MEDICAT|REGIMEN|MONOTHERAP|COMBINATION|DOSE|ASPIRIN|BLOCKER|INHIBITOR|DIURETIC|AMLODIPINE|LOSARTAN/i
const NON_ACTION = /MAINTAIN|CONTINUE|TARGET (?:IS )?(?:REACHED|ACHIEVED)|NO CHANGE/i

export function deriveCareActions(
  recommendation: string,
  options: ActionOption[],
  summary: CriticalSummary,
  context: JsonObject = {},
): string[] {
  const treatment = object(context.treatment)
  const checkpointResults = [
    ['MRA tolerance', treatment?.tolerates_mra],
    ['Spironolactone tolerance', treatment?.tolerates_spironolactone],
  ].flatMap(([label, value]) => typeof value === 'boolean' ? [`${label}: ${value ? 'Yes' : 'No'}`] : [])
  const candidates = [
    ...options.map((option) => option.label),
    ...summary.path
      .filter((step) => step.kind === 'treatment')
      .map((step) => step.label),
    recommendation,
    ...checkpointResults,
  ]
  return Array.from(new Set(candidates.map((item) => item.trim()).filter(
    (item) => item && !MEDICATION.test(item) && !NON_ACTION.test(item),
  )))
}

function object(value: JsonValue | undefined): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value : null
}
