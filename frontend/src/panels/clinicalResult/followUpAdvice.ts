import type { EvaluationResponse, ExecutedAction, JsonObject } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { readableIdentifier } from './decisionPath'
import type { FollowUpAdvice } from './criticalSummaryTypes'

interface FollowUpState {
  risk: string
  pregnancy: boolean
  postpartum: boolean
  immediate: boolean
  activePregnancyHypertension: boolean
}

export function deriveFollowUpAdvice(
  actions: ExecutedAction[],
  pregnancyFollowUp: EvaluationResponse['pregnancy_follow_up'] | undefined,
  state: FollowUpState,
  locale: ClinicalDecisionSupportLocale,
): FollowUpAdvice | null {
  const explicit = explicitFollowUp(actions, locale)
  if (explicit) return explicit
  const required = pregnancyFollowUp?.next_follow_up_required
    || actions.some((action) => action.payload.follow_up_required === true)
    || actions.some((action) => /FOLLOW.?UP|REASSESS/i.test(action.text_en))
  if (!required && !state.immediate) return null
  const vi = locale === 'vi'
  if (state.immediate) {
    return {
      timing: vi ? 'Ngay lập tức / trong ngày' : 'Immediate / same day',
      reason: vi ? 'Nhánh cấp cứu hoặc dấu hiệu nặng đã được kích hoạt.' : 'An emergency or severe-feature branch was triggered.',
      source: vi ? 'Ưu tiên an toàn lâm sàng' : 'Clinical safety override',
    }
  }
  if (state.postpartum) {
    return {
      timing: vi ? 'Trong vòng 7–10 ngày' : 'Within 7–10 days',
      reason: vi ? 'Theo dõi huyết áp sau sinh.' : 'Postpartum blood-pressure review.',
      source: vi ? 'Ngoại lệ theo dõi sản khoa' : 'Obstetric follow-up exception',
    }
  }
  if (state.pregnancy && state.activePregnancyHypertension) {
    return {
      timing: vi ? 'Trong vòng 1 tuần' : 'Within 1 week',
      reason: vi ? 'Tăng huyết áp đang hoạt động trong thai kỳ.' : 'Active hypertension during pregnancy.',
      source: vi ? 'Ngoại lệ theo dõi sản khoa' : 'Obstetric follow-up exception',
    }
  }
  const weeks = ['HIGH', 'VERY_HIGH'].includes(state.risk) ? 2 : state.risk === 'MODERATE' ? 3 : 4
  return {
    timing: vi ? `Trong ${weeks} tuần` : `In ${weeks} weeks`,
    reason: riskReason(state.risk, locale),
    source: vi ? 'Chính sách CDSS dựa trên nguy cơ' : 'Risk-based CDSS policy',
  }
}

function explicitFollowUp(
  actions: ExecutedAction[],
  locale: ClinicalDecisionSupportLocale,
): FollowUpAdvice | null {
  for (const action of actions) {
    const days = numericField(action.payload, 'follow_up_days')
    const weeks = numericField(action.payload, 'follow_up_weeks')
    const minimum = numericField(action.payload, 'follow_up_min_weeks')
    const maximum = numericField(action.payload, 'follow_up_max_weeks')
    if (days === null && weeks === null && (minimum === null || maximum === null)) continue
    const vi = locale === 'vi'
    const timing = days !== null
      ? (vi ? `Trong ${days} ngày` : `In ${days} days`)
      : weeks !== null
        ? (vi ? `Trong ${weeks} tuần` : `In ${weeks} weeks`)
        : (vi ? `Trong ${minimum}–${maximum} tuần` : `In ${minimum}–${maximum} weeks`)
    return {
      timing,
      reason: vi ? 'Khoảng tái khám được chỉ định bởi nhánh điều trị.' : 'The treatment branch specified this review interval.',
      source: vi ? 'Chỉ định rõ trong cây' : 'Explicit tree instruction',
    }
  }
  return null
}

function riskReason(risk: string, locale: ClinicalDecisionSupportLocale): string {
  const label = risk
    ? readableIdentifier(risk)
    : (locale === 'vi' ? 'nguy cơ chưa phân tầng' : 'risk not otherwise stratified')
  return locale === 'vi'
    ? `Lịch tái khám theo mức ${label}.`
    : `Review interval based on ${label.toLowerCase()}.`
}

function numericField(value: JsonObject, key: string): number | null {
  return typeof value[key] === 'number' && Number.isFinite(value[key]) ? value[key] : null
}
