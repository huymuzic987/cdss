import type { ActionOption } from '../clinicalDecisionSupportAdapter'
import type { JsonObject } from '../../api/types'
import type { CriticalSummary } from './criticalSummaryTypes'

const MEDICATION = /DRUG|MEDICAT|REGIMEN|MONOTHERAP|COMBINATION|DOSE|ASPIRIN|BLOCKER|INHIBITOR|DIURETIC|AMLODIPINE|LOSARTAN/i
const NON_ACTION = /MAINTAIN|CONTINUE|TARGET (?:IS )?(?:REACHED|ACHIEVED)|NO CHANGE/i

export function deriveCareActions(
  recommendation: string,
  options: ActionOption[],
  summary: CriticalSummary,
  _context: JsonObject = {},
): string[] {
  const candidates = [
    ...options.map((option) => option.label),
    ...summary.path
      .filter((step) => !isResistantToleranceCheck(step.id))
      .filter((step) => step.kind === 'treatment')
      .map((step) => step.label),
    recommendation,
  ]
  return Array.from(new Set(candidates.map((item) => item.trim()).filter(
    (item) => item && !MEDICATION.test(item) && !NON_ACTION.test(item),
  )))
}

function isResistantToleranceCheck(stepId: string): boolean {
  return /:T13_A_CHECK_(?:MRA|SPIRONOLACTONE)$/.test(stepId)
}
