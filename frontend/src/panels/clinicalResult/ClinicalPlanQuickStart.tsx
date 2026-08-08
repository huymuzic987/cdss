import { useState } from 'react'
import type { ClinicalPlanItemInput } from '../../api/types'

interface ClinicalPlanQuickStartProps {
  locale: 'en' | 'vi'
  onAdd: (item: ClinicalPlanItemInput) => void
  onError: () => void
}

export function ClinicalPlanQuickStart({ locale, onAdd, onError }: ClinicalPlanQuickStartProps) {
  const [sbp, setSbp] = useState('')
  const [dbp, setDbp] = useState('')
  const [map, setMap] = useState('')
  const addFollowUp = (weeks: number) => {
    const scheduledAt = new Date()
    scheduledAt.setDate(scheduledAt.getDate() + weeks * 7)
    onAdd({ type: 'NEXT_FOLLOW_UP', scheduled_at: scheduledAt.toISOString(), duration_value: weeks, duration_unit: 'weeks' })
  }
  const addBpTarget = () => {
    const targetSbp = Number(sbp), targetDbp = Number(dbp)
    if (!Number.isFinite(targetSbp) || !Number.isFinite(targetDbp) || targetSbp <= 0 || targetDbp <= 0) return onError()
    onAdd({ type: 'TARGET_BP', target_mode: 'SBP_DBP', target_sbp: targetSbp, target_dbp: targetDbp })
  }
  const addMapTarget = () => {
    const targetMap = Number(map)
    if (!Number.isFinite(targetMap) || targetMap <= 0 || targetMap > 100) return onError()
    onAdd({ type: 'TARGET_BP', target_mode: 'MAP_REDUCTION_PERCENT', map_reduction_percent: targetMap })
  }
  return (
    <div className="cds-plan-quick-start">
      <div className="cds-plan-quick-heading"><strong>{locale === 'vi' ? 'Dùng ngay' : 'Use right away'}</strong><small>{locale === 'vi' ? 'Các mốc theo dõi thường dùng' : 'Popular milestones for a quick plan'}</small></div>
      <div className="cds-plan-quick-followups">{[1, 2, 4].map((weeks) => <button type="button" key={weeks} onClick={() => addFollowUp(weeks)}><strong>{weeks}</strong><span>{locale === 'vi' ? 'tuần' : weeks === 1 ? 'week' : 'weeks'}</span><small>{locale === 'vi' ? 'Tái khám' : 'Follow-up'}</small></button>)}</div>
      <div className="cds-plan-quick-targets">
        <div className="cds-plan-quick-target-group"><span>{locale === 'vi' ? 'Mục tiêu SBP / DBP' : 'SBP / DBP target'}</span><label><input aria-label="Quick target SBP" type="number" min="1" max="400" placeholder="SBP" value={sbp} onChange={(event) => setSbp(event.target.value)} /><input aria-label="Quick target DBP" type="number" min="1" max="300" placeholder="DBP" value={dbp} onChange={(event) => setDbp(event.target.value)} /><button type="button" className="primary" onClick={addBpTarget}>+</button></label></div>
        <div className="cds-plan-quick-target-group"><span>{locale === 'vi' ? 'Mục tiêu MAP' : 'MAP target'}</span><label><input aria-label="Quick MAP reduction percentage" type="number" min="1" max="100" step="0.1" placeholder="%" value={map} onChange={(event) => setMap(event.target.value)} /><button type="button" className="primary" onClick={addMapTarget}>+</button></label></div>
      </div>
    </div>
  )
}
