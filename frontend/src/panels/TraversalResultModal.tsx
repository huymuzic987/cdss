import { useEffect, useRef, useState } from 'react'
import type { ApiErrorResponse, ClinicalPlanItemInput, EvaluationResponse, JsonObject, TreeGraphResponse } from '../api/types'
import { saveRegimenDecision } from '../api/client'
import { buildClinicalPresentation } from './clinicalDecisionSupportAdapter'
import { getClinicalDecisionSupportMessages, type ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'
import { deriveAlertTitle, isHypertensionLabel, titleContainsFinding } from './clinicalResult/alertTitle'
import { deriveCareActions } from './clinicalResult/careActions'
import { confirmedText } from './clinicalResult/criticalFindingFormat'
import { deriveCriticalSummary } from './clinicalResult/criticalSummary'
import { deriveMedicationFollowUpMessage } from './clinicalResult/medicationFollowUpMessage'
import { actionWithPresentation, deriveMedicationReassessment, withCurrentFollowUpRegimen } from './clinicalResult/modalHelpers'
import { buildOrderProvenance } from './clinicalResult/orderProvenance'
import { RegimenDecisionEditor } from './clinicalResult/RegimenDecisionEditor'
import { TraversalResultBody } from './TraversalResultBody'

export type { RecommendedOrder } from './clinicalDecisionSupportAdapter'

interface TraversalResultModalProps { result: EvaluationResponse | null, partial: ApiErrorResponse | null, graphs?: Record<string, TreeGraphResponse>, onClose: () => void, locale?: ClinicalDecisionSupportLocale }

function optionSelections(presentation: ReturnType<typeof buildClinicalPresentation>) {
  return presentation.regimenOptions.filter((option) => option.components.length > 0).map((option) => ({ components: option.components.map((component) => ({ selector_kind: component.selectorKind ?? (component.medicineId ? 'medicine' : component.subgroup ? 'subgroup' : 'group'), group_code: component.group, ...(component.subgroup ? { subgroup: component.subgroup } : {}), ...(component.medicineId ? { medicine_id: component.medicineId } : {}), dose_strategy: component.doseStrategy ?? 'LOW_DOSE' })) }))
}

function ResultDialog({ result, partial, graphs = {}, onClose, locale }: Omit<TraversalResultModalProps, 'locale'> & { locale: ClinicalDecisionSupportLocale }) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const state = partial?.partial_run_state
  const inputSnapshot = result?.input_snapshot ?? state?.input_snapshot ?? {}
  const actions = result?.actions ?? state?.actions ?? []
  const context = result?.context ?? state?.context ?? {}
  const log = result?.traversal_log ?? state?.traversal_log ?? []
  const references = result?.references ?? state?.references ?? []
  const presentation = buildClinicalPresentation(actions, inputSnapshot, context, locale)
  const summary = deriveCriticalSummary({ log, actions, context, graphs, locale, pregnancyFollowUp: result?.pregnancy_follow_up })
  const alertTitle = deriveAlertTitle(log, graphs, summary.path, inputSnapshot, locale)
  const confirmation = confirmedText(locale)
  const confirmedFindings = summary.findings.filter((finding) => finding.value === confirmation && !isHypertensionLabel(finding.label) && !titleContainsFinding(alertTitle, finding.label))
  const detailedFindings = summary.findings.filter((finding) => finding.value !== confirmation)
  const recommendationAction = actionWithPresentation(actions) ?? actions.at(-1)
  const provenance = buildOrderProvenance(recommendationAction, references, graphs, locale)
  const medicationFollowUpMessage = deriveMedicationFollowUpMessage(actions, context, locale)
  const medicationReassessment = deriveMedicationReassessment(context, locale)
  const displayedOrders = withCurrentFollowUpRegimen(presentation.orders, context, locale)
  const careActions = deriveCareActions(presentation.recommendation, presentation.additionalActions, summary, context)
  if (medicationFollowUpMessage && !careActions.includes(medicationFollowUpMessage)) careActions.unshift(medicationFollowUpMessage)
  const baselineClinicalPlan: ClinicalPlanItemInput[] = careActions.map((text) => ({ type: 'ELSE', text }))
  const [editing, setEditing] = useState(false)
  const [savingDecision, setSavingDecision] = useState(false)
  const [decisionError, setDecisionError] = useState<string>()
  const dialogRef = useRef<HTMLDivElement>(null)
  const acceptRegimen = async () => {
    if (!result) return
    setSavingDecision(true); setDecisionError(undefined)
    try { await saveRegimenDecision({ outcome: 'accepted', evaluation_snapshot: result as unknown as JsonObject, baseline: { clinical_plan: baselineClinicalPlan, regimen_options: optionSelections(presentation) }, rejection_reasons: [] }); onClose() } catch (reason: unknown) { setDecisionError(reason instanceof Error ? reason.message : (locale === 'vi' ? 'Không thể lưu quyết định.' : 'Unable to save decision.')) } finally { setSavingDecision(false) }
  }
  useEffect(() => {
    dialogRef.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      if (editing) setEditing(false)
      else onClose()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [editing, onClose])
  return <div className="modal-overlay" onMouseDown={(event) => event.target === event.currentTarget && !editing && onClose()}>
    <div ref={dialogRef} className="modal-box cds-modal" role="dialog" aria-modal="true" aria-label={messages.recommendationTitle} tabIndex={-1}>
      <TraversalResultBody result={result} partial={partial} messages={messages} summary={summary} alertTitle={alertTitle} confirmation={confirmation} confirmedFindings={confirmedFindings} detailedFindings={detailedFindings} careActions={careActions} medicationReassessment={medicationReassessment} displayedOrders={displayedOrders} provenance={provenance} presentation={presentation} references={references} locale={locale} />
      {result && <>{decisionError && <p className="cds-decision-error">{decisionError}</p>}<div className="cds-decision-actions"><button type="button" onClick={() => void acceptRegimen()} disabled={savingDecision}>{locale === 'vi' ? 'Chấp nhận phác đồ' : 'Accept regimen'}</button><button type="button" className="primary" onClick={() => setEditing(true)} disabled={savingDecision}>{locale === 'vi' ? 'Từ chối phác đồ' : 'Reject regimen'}</button></div></>}
    </div>
    {result && <RegimenDecisionEditor open={editing} result={result} presentation={presentation} summary={summary} alertTitle={alertTitle} confirmedFindings={confirmedFindings} detailedFindings={detailedFindings} baselineClinicalPlan={baselineClinicalPlan} locale={locale} onBack={() => setEditing(false)} onSaved={onClose} />}
  </div>
}

export function TraversalResultModal({ locale, ...props }: TraversalResultModalProps) {
  if (!props.result && !props.partial) return null
  const resolvedLocale = locale ?? (document.documentElement.lang.toLowerCase().startsWith('vi') ? 'vi' : 'en')
  return <ResultDialog {...props} locale={resolvedLocale} />
}
