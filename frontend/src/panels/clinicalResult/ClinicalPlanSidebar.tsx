import { useState } from 'react'
import type {
  ClinicalPlanItemInput,
  DurationUnit,
  TargetMode,
  TimeframeUnit,
} from '../../api/types'

type PlanTab = 'NEXT_FOLLOW_UP' | 'TARGET_BP' | 'ELSE'

interface ClinicalPlanSidebarProps {
  open: boolean
  locale: 'en' | 'vi'
  onCancel: () => void
  onAdd: (item: ClinicalPlanItemInput) => void
}

const copy = {
  en: {
    title: 'Add clinical-plan row',
    followUp: 'Next follow-up meeting',
    target: 'Target BP',
    other: 'Else',
    date: 'Date',
    time: 'Time',
    duration: 'Duration until meeting',
    amount: 'Amount',
    unit: 'Unit',
    weeks: 'Weeks',
    months: 'Months',
    mode: 'Target type',
    sbpDbp: 'SBP / DBP',
    mapPercent: 'MAP reduction %',
    sbp: 'Target SBP',
    dbp: 'Target DBP',
    map: 'Reduction percentage',
    timeframe: 'Within (optional)',
    days: 'Days',
    text: 'Plan text',
    cancel: 'Cancel',
    add: 'Add',
    required: 'Complete the required fields before adding this row.',
  },
  vi: {
    title: 'Thêm dòng kế hoạch lâm sàng',
    followUp: 'Lần tái khám tiếp theo',
    target: 'Đích huyết áp',
    other: 'Khác',
    date: 'Ngày',
    time: 'Giờ',
    duration: 'Thời lượng đến cuộc hẹn',
    amount: 'Số lượng',
    unit: 'Đơn vị',
    weeks: 'Tuần',
    months: 'Tháng',
    mode: 'Loại mục tiêu',
    sbpDbp: 'Tâm thu / tâm trương',
    mapPercent: '% giảm MAP',
    sbp: 'Tâm thu mục tiêu',
    dbp: 'Tâm trương mục tiêu',
    map: 'Phần trăm giảm',
    timeframe: 'Trong khoảng (tuỳ chọn)',
    days: 'Ngày',
    text: 'Nội dung kế hoạch',
    cancel: 'Huỷ',
    add: 'Thêm',
    required: 'Hãy điền đủ các trường bắt buộc trước khi thêm dòng.',
  },
} as const

export function ClinicalPlanSidebar({
  open, locale, onCancel, onAdd,
}: ClinicalPlanSidebarProps) {
  const messages = copy[locale]
  const [tab, setTab] = useState<PlanTab>('NEXT_FOLLOW_UP')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [durationValue, setDurationValue] = useState('')
  const [durationUnit, setDurationUnit] = useState<DurationUnit>('weeks')
  const [targetMode, setTargetMode] = useState<TargetMode>('SBP_DBP')
  const [targetSbp, setTargetSbp] = useState('')
  const [targetDbp, setTargetDbp] = useState('')
  const [mapReduction, setMapReduction] = useState('')
  const [timeframeValue, setTimeframeValue] = useState('')
  const [timeframeUnit, setTimeframeUnit] = useState<TimeframeUnit>('weeks')
  const [text, setText] = useState('')
  const [error, setError] = useState(false)

  if (!open) return null

  const add = () => {
    setError(false)
    if (tab === 'NEXT_FOLLOW_UP') {
      if (!date || !time) return setError(true)
      const item: ClinicalPlanItemInput = {
        type: tab,
        scheduled_at: new Date(`${date}T${time}`).toISOString(),
      }
      if (durationValue) {
        const amount = Number(durationValue)
        if (!Number.isFinite(amount) || amount <= 0) return setError(true)
        item.duration_value = amount
        item.duration_unit = durationUnit
      }
      onAdd(item)
      return
    }
    if (tab === 'TARGET_BP') {
      const timeframe = timeframeValue ? Number(timeframeValue) : undefined
      if (timeframeValue && (!Number.isFinite(timeframe) || timeframe! <= 0)) return setError(true)
      const item: ClinicalPlanItemInput = {
        type: tab,
        target_mode: targetMode,
        ...(timeframe ? { timeframe_value: timeframe, timeframe_unit: timeframeUnit } : {}),
      }
      if (targetMode === 'SBP_DBP') {
        const sbp = Number(targetSbp)
        const dbp = Number(targetDbp)
        if (!Number.isFinite(sbp) || !Number.isFinite(dbp) || sbp <= 0 || dbp <= 0) return setError(true)
        item.target_sbp = sbp
        item.target_dbp = dbp
      } else {
        const percentage = Number(mapReduction)
        if (!Number.isFinite(percentage) || percentage <= 0 || percentage > 100) return setError(true)
        item.map_reduction_percent = percentage
      }
      onAdd(item)
      return
    }
    if (!text.trim()) return setError(true)
    onAdd({ type: tab, text: text.trim() })
  }

  return (
    <aside className="cds-plan-sidebar" role="dialog" aria-label={messages.title}>
      <div className="cds-editor-drawer-heading">
        <strong>{messages.title}</strong>
        <button type="button" onClick={onCancel} aria-label={messages.cancel}>×</button>
      </div>
      <div className="cds-plan-tabs" role="tablist">
        {([
          ['NEXT_FOLLOW_UP', messages.followUp],
          ['TARGET_BP', messages.target],
          ['ELSE', messages.other],
        ] as const).map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            className={tab === value ? 'active' : ''}
            onClick={() => { setTab(value); setError(false) }}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'NEXT_FOLLOW_UP' && (
        <div className="cds-editor-form-grid">
          <label>{messages.date}<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
          <label>{messages.time}<input type="time" value={time} onChange={(event) => setTime(event.target.value)} /></label>
          <label>{messages.duration}<input type="number" min="0" step="0.5" value={durationValue} onChange={(event) => setDurationValue(event.target.value)} /></label>
          <label>{messages.unit}<select value={durationUnit} onChange={(event) => setDurationUnit(event.target.value as DurationUnit)}><option value="weeks">{messages.weeks}</option><option value="months">{messages.months}</option></select></label>
        </div>
      )}

      {tab === 'TARGET_BP' && (
        <div className="cds-editor-form-grid">
          <label>{messages.mode}<select value={targetMode} onChange={(event) => setTargetMode(event.target.value as TargetMode)}><option value="SBP_DBP">{messages.sbpDbp}</option><option value="MAP_REDUCTION_PERCENT">{messages.mapPercent}</option></select></label>
          {targetMode === 'SBP_DBP' ? <>
            <label>{messages.sbp}<input type="number" min="1" max="400" value={targetSbp} onChange={(event) => setTargetSbp(event.target.value)} /></label>
            <label>{messages.dbp}<input type="number" min="1" max="300" value={targetDbp} onChange={(event) => setTargetDbp(event.target.value)} /></label>
          </> : <label>{messages.map}<input type="number" min="1" max="100" step="0.1" value={mapReduction} onChange={(event) => setMapReduction(event.target.value)} /></label>}
          <label>{messages.timeframe}<input type="number" min="0" step="0.5" value={timeframeValue} onChange={(event) => setTimeframeValue(event.target.value)} /></label>
          <label>{messages.unit}<select value={timeframeUnit} onChange={(event) => setTimeframeUnit(event.target.value as TimeframeUnit)}><option value="days">{messages.days}</option><option value="weeks">{messages.weeks}</option><option value="months">{messages.months}</option></select></label>
        </div>
      )}

      {tab === 'ELSE' && <label className="cds-editor-textarea-label">{messages.text}<textarea rows={7} value={text} onChange={(event) => setText(event.target.value)} /></label>}
      {error && <p className="cds-editor-validation-error">{messages.required}</p>}
      <div className="cds-editor-drawer-actions"><button type="button" onClick={onCancel}>{messages.cancel}</button><button type="button" className="primary" onClick={add}>{messages.add}</button></div>
    </aside>
  )
}
