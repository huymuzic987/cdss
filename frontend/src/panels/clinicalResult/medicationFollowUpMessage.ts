import type { ExecutedAction, JsonObject, JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

const STOP_OUTCOMES = new Set([
  'REPLACE_DRUG_SAME_STAGE',
  'CONTINUE_UNTIL_REASSESSMENT',
  'ADDRESS_ADHERENCE_OR_DOSE',
])

const MAINTAIN_CONTROLLED = 'MAINTAIN_CONTROLLED'

export function deriveMedicationFollowUpMessage(
  actions: ExecutedAction[],
  context: JsonObject,
  locale: ClinicalDecisionSupportLocale,
): string | null {
  const followUp = object(context.medication_follow_up)
  const contextOutcome = stringValue(followUp?.outcome)
  if (contextOutcome === MAINTAIN_CONTROLLED) {
    return locale === 'vi'
      ? 'Huyết áp đã đạt mục tiêu. Tiếp tục theo dõi và duy trì phác đồ hiện tại.'
      : 'Blood pressure target met. Continue monitoring and maintain the current regimen.'
  }
  const action = [...actions].reverse().find((candidate) => {
    const actionType = stringValue(candidate.payload.action_type)
    return STOP_OUTCOMES.has(actionType)
      || (actionType === '' && STOP_OUTCOMES.has(contextOutcome))
  })
  if (!action) return null
  return locale === 'vi' ? action.text_vi || action.text_en : action.text_en || action.text_vi
}

function object(value: JsonValue | undefined): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value : null
}

function stringValue(value: JsonValue | undefined): string {
  return typeof value === 'string' ? value : ''
}
