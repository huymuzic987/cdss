import type {
  EvaluationResponse,
  ExecutedAction,
  JsonObject,
} from '../../api/types'
import { formatVisitDate } from './criticalFindingFormat'
import type { RecommendedOrder } from '../clinicalDecisionSupportAdapter'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

export function deriveMedicationReassessment(
  context: EvaluationResponse['context'],
  locale: ClinicalDecisionSupportLocale,
): { date: string } | null {
  const followUpValue = context.medication_follow_up
  const followUp = typeof followUpValue === 'object' && followUpValue !== null && !Array.isArray(followUpValue)
    ? followUpValue : null
  const reassessment = typeof followUp?.next_follow_up_date === 'string'
    ? followUp.next_follow_up_date : null
  return reassessment ? { date: formatVisitDate(reassessment, locale) } : null
}

export function withCurrentFollowUpRegimen(
  orders: RecommendedOrder[],
  context: JsonObject,
  locale: ClinicalDecisionSupportLocale,
): RecommendedOrder[] {
  const hasNewCombination = orders.some((order) => order.orderType === 'medication'
    && (order.drugClasses?.length ?? 0) > 1
    && order.drugClasses!.every(({ code }) => /^[ABCD]$/.test(code)))
  if (hasNewCombination) return orders
  const value = context.medication_follow_up
  const followUp = typeof value === 'object' && value !== null && !Array.isArray(value) ? value : null
  const rawClasses = followUp?.current_regimen_drug_classes
  const classes = Array.isArray(rawClasses)
    ? rawClasses.filter((item): item is string => typeof item === 'string' && /^[ABCD]$/.test(item))
    : []
  if (classes.length === 0) return orders
  const currentLabel = locale === 'vi' ? 'Phác đồ hiện tại' : 'Current regimen'
  return [...orders, {
    id: 'medication-follow-up-current-regimen',
    name: currentLabel,
    classLabel: classes.join(' + '),
    orderType: 'current-regimen',
    drugClasses: classes.map((code) => ({
      code,
      label: locale === 'vi' ? `Nhóm thuốc ${code}` : `Drug Class ${code}`,
      doseLabel: '',
      medicines: [],
    })),
  }]
}

export function actionWithPresentation(actions: ExecutedAction[]): ExecutedAction | undefined {
  return [...actions].reverse().find((action) => {
    const value = action.payload.presentation
    return typeof value === 'object' && value !== null && !Array.isArray(value)
  })
}
