import { useEffect, useMemo, useState } from 'react'
import type { ClinicalPlanItemInput, EvaluationResponse, JsonObject, MedicineCatalogResponse, RejectionReasonCode, RegimenDecisionCreateRequest } from '../../api/types'
import { fetchMedicineCatalog, saveRegimenDecision } from '../../api/client'
import type { ClinicalPresentation, FinalRegimenOption } from '../clinicalPresentation/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { ClinicalSection } from './ClinicalSection'
import { ClinicalPlanSidebar } from './ClinicalPlanSidebar'
import { EditableRegimen } from './EditableRegimen'
import type { ImportantPathStep } from './criticalSummaryTypes'
import { ImportantDecisionPath } from './ImportantDecisionPath'
import { RegimenPathDisplay } from './RegimenPathDisplay'
import { RegimenComparisonDialog } from './RegimenComparisonDialog'
import { createRegimenSafetyWarningResolver } from './regimenSafetyWarnings'
import './RegimenDecisionEditor.css'

interface Finding { id: string, label: string, value: string, treeName: string }
interface Summary { urgency: string, urgencyLabel: string, findings: Finding[], path: ImportantPathStep[] }
interface ReasonLabel { code: RejectionReasonCode, en: string, vi: string }

interface RegimenDecisionEditorProps {
  open: boolean
  result: EvaluationResponse
  presentation: ClinicalPresentation
  summary: Summary
  alertTitle: string
  confirmedFindings: Finding[]
  detailedFindings: Finding[]
  baselineClinicalPlan: ClinicalPlanItemInput[]
  locale: ClinicalDecisionSupportLocale
  onBack: () => void
  onSaved: () => void
}

const reasonCodes: ReasonLabel[] = [
  { code: 'DRUGS_NOT_CORRECT', en: 'Drugs not correct', vi: 'Thuốc chưa phù hợp' },
  { code: 'DOSE_OR_FREQUENCY_NOT_CORRECT', en: 'Dose or frequency incorrect', vi: 'Liều hoặc tần suất chưa đúng' },
  { code: 'SAFETY_OR_CONTRAINDICATION', en: 'Safety / contraindication', vi: 'An toàn / chống chỉ định' },
  { code: 'PATIENT_PREFERENCE_OR_ADHERENCE', en: 'Patient preference / adherence', vi: 'Ưu tiên / khả năng tuân thủ của bệnh nhân' },
  { code: 'AVAILABILITY_OR_COST', en: 'Availability / cost', vi: 'Khả năng cung ứng / chi phí' },
  { code: 'OTHER', en: 'Other', vi: 'Khác' },
]

function selections(options: FinalRegimenOption[]) {
  return options.filter((option) => option.components.length > 0).map((option) => ({ components: option.components.map((component) => ({
    selector_kind: component.selectorKind ?? (component.medicineId ? 'medicine' : component.subgroup ? 'subgroup' : 'group'), group_code: component.group,
    ...(component.subgroup ? { subgroup: component.subgroup } : {}), ...(component.medicineId ? { medicine_id: component.medicineId } : {}), dose_strategy: component.doseStrategy ?? 'LOW_DOSE',
  })) }))
}

function planLabel(item: ClinicalPlanItemInput, locale: ClinicalDecisionSupportLocale): string {
  const vi = locale === 'vi'
  if (item.type === 'NEXT_FOLLOW_UP') return `${vi ? 'Tái khám' : 'Follow-up'}: ${item.scheduled_at ? new Date(item.scheduled_at).toLocaleString(vi ? 'vi-VN' : 'en-US') : ''}${item.duration_value ? ` · ${item.duration_value} ${item.duration_unit}` : ''}`
  if (item.type === 'TARGET_BP') {
    const target = item.target_mode === 'MAP_REDUCTION_PERCENT' ? `${item.map_reduction_percent}% MAP reduction` : `${item.target_sbp}/${item.target_dbp} mmHg`
    return `${vi ? 'Mục tiêu huyết áp' : 'Target BP'}: ${target}${item.timeframe_value ? ` · ${item.timeframe_value} ${item.timeframe_unit}` : ''}`
  }
  return item.text ?? ''
}

function rows(options: FinalRegimenOption[], plan: ClinicalPlanItemInput[], locale: ClinicalDecisionSupportLocale): string[] {
  return [...plan.map((item) => planLabel(item, locale)), ...options.filter((option) => option.components.length > 0).map((option, index) => `${locale === 'vi' ? 'Lựa chọn' : 'Option'} ${index + 1}: ${option.components.map((component) => component.label).join(' + ')}`)]
}

function copyOptions(options: FinalRegimenOption[]): FinalRegimenOption[] {
  return options.length > 0
    ? options.map((option) => ({ ...option, components: option.components.map((component) => ({ ...component })) }))
    : [{ id: 'regimen-option-1', components: [] }]
}

export function RegimenDecisionEditor({ open, result, presentation, summary, alertTitle, confirmedFindings, detailedFindings, baselineClinicalPlan, locale, onBack, onSaved }: RegimenDecisionEditorProps) {
  const vi = locale === 'vi'
  const [catalog, setCatalog] = useState<MedicineCatalogResponse['groups']>([])
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState<string>()
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [planItems, setPlanItems] = useState(baselineClinicalPlan)
  const [options, setOptions] = useState<FinalRegimenOption[]>(() => copyOptions(presentation.regimenOptions))
  const [planSidebarOpen, setPlanSidebarOpen] = useState(false)
  const [reasons, setReasons] = useState<RejectionReasonCode[]>([])
  const [otherReason, setOtherReason] = useState('')
  const [comparisonOpen, setComparisonOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>()

  useEffect(() => {
    if (!open) return
    setCatalogOpen(false)
    setPlanSidebarOpen(false)
    setComparisonOpen(false)
    setPlanItems(baselineClinicalPlan)
    setOptions(copyOptions(presentation.regimenOptions))
    setReasons([])
    setOtherReason('')
    setError(undefined)
  }, [baselineClinicalPlan, open, presentation.regimenOptions])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setCatalogLoading(true)
    setCatalogError(undefined)
    fetchMedicineCatalog().then((response) => { if (!cancelled) setCatalog(response.groups) }).catch((reason: unknown) => { if (!cancelled) setCatalogError(reason instanceof Error ? reason.message : 'Unable to load medicine catalog') }).finally(() => { if (!cancelled) setCatalogLoading(false) })
    return () => { cancelled = true }
  }, [open])

  const baselineSubgroups = useMemo(() => Object.fromEntries(
    Object.entries(presentation.regimenCatalog)
      .filter(([group]) => group !== '__all__')
      .map(([group, medicines]) => [group, Array.from(new Set(medicines.map((medicine) => medicine.subgroup).filter(Boolean)))]),
  ), [presentation.regimenCatalog])
  const currentSubgroups = useMemo(() => catalog.length > 0
    ? Object.fromEntries(catalog.map((group) => [group.code, group.subgroups.map((subgroup) => subgroup.name)]))
    : baselineSubgroups, [baselineSubgroups, catalog])
  const baselineOptions = presentation.regimenOptions
  const safetyWarnings = useMemo(() => createRegimenSafetyWarningResolver(catalog, presentation, result, locale), [catalog, locale, presentation, result])
  const baselineRows = useMemo(() => rows(baselineOptions, baselineClinicalPlan, locale), [baselineClinicalPlan, baselineOptions, locale])
  const customRows = useMemo(() => rows(options, planItems, locale), [locale, options, planItems])
  const hasOther = reasons.includes('OTHER')
  const baselinePlanCount = baselineClinicalPlan.length

  const toggleReason = (code: RejectionReasonCode) => {
    setReasons((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code])
    setError(undefined)
  }

  const requestSave = () => {
    setError(undefined)
    if (reasons.length === 0) return setError(vi ? 'Chọn ít nhất một lý do từ chối.' : 'Select at least one rejection reason.')
    if (hasOther && !otherReason.trim()) return setError(vi ? 'Vui lòng nhập lý do khác.' : 'Enter details for the Other reason.')
    setComparisonOpen(true)
  }

  const confirmSave = async () => {
    setSaving(true)
    setError(undefined)
    const payload: RegimenDecisionCreateRequest = {
      outcome: 'rejected',
      evaluation_snapshot: result as unknown as JsonObject,
      baseline: { clinical_plan: baselineClinicalPlan, regimen_options: selections(baselineOptions) },
      final: { clinical_plan: planItems, regimen_options: selections(options) },
      rejection_reasons: reasons,
      ...(otherReason.trim() ? { other_rejection_reason: otherReason.trim() } : {}),
    }
    try {
      await saveRegimenDecision(payload)
      setComparisonOpen(false)
      onSaved()
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : (vi ? 'Không thể lưu phác đồ.' : 'Unable to save regimen.'))
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null
  return (
    <div className="cds-editor-overlay" onMouseDown={(event) => event.target === event.currentTarget && onBack()}>
      <div className="cds-editor-modal" role="dialog" aria-modal="true" aria-label={vi ? 'Chỉnh sửa phác đồ' : 'Edit regimen'}>
        <div className="cds-editor-header"><div><span className="cds-editor-eyebrow">{vi ? 'Tùy chỉnh quyết định' : 'Decision customization'}</span><h2>{vi ? 'Chỉnh sửa phác đồ cuối cùng' : 'Edit final regimen'}</h2></div><button type="button" onClick={onBack}>×</button></div>
        <div className="cds-editor-body">
          <ClinicalSection title={vi ? 'Cảnh báo' : 'Alert'} className={`cds-alert-${summary.urgency}`}><div className="cds-alert-row"><div className="cds-row-heading"><span className="cds-urgency-badge">{summary.urgencyLabel}</span><strong>{alertTitle}</strong>{confirmedFindings.length > 0 && <span className="cds-confirmed-tags">{confirmedFindings.map((finding) => <span className="cds-confirmed-tag" key={finding.id}>{finding.label}</span>)}</span>}</div></div></ClinicalSection>
          <ClinicalSection title={vi ? 'Phát hiện của bệnh nhân' : 'Patient findings'}>{detailedFindings.length === 0 ? <p className="cds-empty">{vi ? 'Không có bằng chứng bổ sung.' : 'No additional evidence.'}</p> : <div className="cds-data-rows">{detailedFindings.map((finding) => <div className="cds-data-row" key={finding.id}><span>{finding.label}<small>{finding.treeName}</small></span><strong>{finding.value}</strong></div>)}</div>}</ClinicalSection>
          <ClinicalSection title={vi ? 'Kế hoạch lâm sàng' : 'Clinical Plan'} action={<button type="button" className="cds-section-plus" onClick={() => setPlanSidebarOpen(true)}>+</button>}><div className="cds-plan-rows">{planItems.length === 0 && <p className="cds-empty">{vi ? 'Chưa có kế hoạch.' : 'No clinical-plan rows yet.'}</p>}{planItems.map((item, index) => <div className={`cds-plan-row${index < baselinePlanCount ? ' cds-plan-row-default' : ''}`} key={`${item.type}-${index}`}><span><small className="cds-plan-origin">{index < baselinePlanCount ? (vi ? 'Mặc định' : 'Default') : (vi ? 'Tùy chỉnh' : 'Custom')}</small>{planLabel(item, locale)}</span>{index >= baselinePlanCount && <button type="button" onClick={() => setPlanItems((current) => current.filter((_, rowIndex) => rowIndex !== index))}>×</button>}</div>)}</div><ClinicalPlanSidebar open={planSidebarOpen} locale={locale} onCancel={() => setPlanSidebarOpen(false)} onAdd={(item) => { setPlanItems((current) => [...current, item]); setPlanSidebarOpen(false) }} /></ClinicalSection>
          <ClinicalSection title={vi ? 'Phác đồ thuốc cuối cùng' : 'Final drug regimen'} action={<button type="button" className="cds-section-plus" onClick={() => setCatalogOpen((current) => !current)}>+</button>}><EditableRegimen locale={locale} options={options} catalog={catalog} currentSubgroups={currentSubgroups} baselineSubgroups={baselineSubgroups} catalogOpen={catalogOpen} catalogLoading={catalogLoading} catalogError={catalogError} safetyWarnings={safetyWarnings} onCatalogOpenChange={setCatalogOpen} onChange={setOptions} /></ClinicalSection>
          <ClinicalSection title={vi ? 'Lý do từ chối' : 'Reason for rejecting'}><div className="cds-rejection-reasons">{reasonCodes.map((reason) => <label key={reason.code}><input type="checkbox" checked={reasons.includes(reason.code)} onChange={() => toggleReason(reason.code)} />{vi ? reason.vi : reason.en}</label>)}</div>{hasOther && <label className="cds-editor-textarea-label">{vi ? 'Mô tả lý do khác (chi tiết tùy chọn)' : 'Describe the Other reason (optional details)'}<textarea rows={5} value={otherReason} onChange={(event) => setOtherReason(event.target.value)} /></label>}</ClinicalSection>
          <ClinicalSection title={vi ? 'Đường đi quyết định quan trọng' : 'Important decision path'} subtitle={`${summary.path.length} · ${vi ? 'các bước ảnh hưởng quyết định' : 'decision-shaping steps'}`} className="cds-path-details" defaultOpen={false}><ImportantDecisionPath steps={summary.path} emptyText={vi ? 'Không có đường đi quan trọng.' : 'No important path.'} /><RegimenPathDisplay presentation={presentation} locale={locale} /></ClinicalSection>
        </div>
        {error && <p className="cds-editor-save-error">{error}</p>}
        <div className="cds-editor-actions"><button type="button" onClick={onBack}>{vi ? 'Quay lại' : 'Back'}</button><button type="button" className="primary" onClick={requestSave}>{vi ? 'Lưu phác đồ' : 'Save regimen'}</button></div>
      </div>
      {comparisonOpen && <RegimenComparisonDialog locale={locale} baselineRows={baselineRows} customRows={customRows} reasons={reasons} reasonCodes={reasonCodes} saving={saving} onCancel={() => setComparisonOpen(false)} onConfirm={() => void confirmSave()} />}
    </div>
  )
}
