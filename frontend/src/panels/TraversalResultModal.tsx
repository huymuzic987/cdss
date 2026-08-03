import { useEffect, useRef } from 'react'
import type { ApiErrorResponse, EvaluationResponse, TreeGraphResponse } from '../api/types'
import { buildClinicalPresentation } from './clinicalDecisionSupportAdapter'
import {
  getClinicalDecisionSupportMessages,
  type ClinicalDecisionSupportLocale,
} from './clinicalDecisionSupportMessages'
import { deriveAlertTitle, isHypertensionLabel, titleContainsFinding } from './clinicalResult/alertTitle'
import { deriveCareActions } from './clinicalResult/careActions'
import { ClinicalSection } from './clinicalResult/ClinicalSection'
import { confirmedText, formatVisitDate } from './clinicalResult/criticalFindingFormat'
import { deriveCriticalSummary } from './clinicalResult/criticalSummary'
import { ImportantDecisionPath } from './clinicalResult/ImportantDecisionPath'
import { deriveMedicationFollowUpMessage } from './clinicalResult/medicationFollowUpMessage'
import { actionWithPresentation, deriveMedicationReassessment, withCurrentFollowUpRegimen } from './clinicalResult/modalHelpers'
import { buildOrderProvenance } from './clinicalResult/orderProvenance'
import {
  isSingleMedicationOrder,
  RecommendedOrderCard,
} from './clinicalResult/RecommendedOrderCard'

export type { RecommendedOrder } from './clinicalDecisionSupportAdapter'

interface TraversalResultModalProps {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  graphs?: Record<string, TreeGraphResponse>
  onClose: () => void
  locale?: ClinicalDecisionSupportLocale
}

function ResultDialog({
  result, partial, graphs = {}, onClose, locale,
}: Omit<TraversalResultModalProps, 'locale'> & { locale: ClinicalDecisionSupportLocale }) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const state = partial?.partial_run_state
  const inputSnapshot = result?.input_snapshot ?? state?.input_snapshot ?? {}
  const actions = result?.actions ?? state?.actions ?? []
  const context = result?.context ?? state?.context ?? {}
  const log = result?.traversal_log ?? state?.traversal_log ?? []
  const references = result?.references ?? state?.references ?? []
  const presentation = buildClinicalPresentation(actions, inputSnapshot, context, locale)
  const summary = deriveCriticalSummary({
    log, actions, context, graphs, locale,
    pregnancyFollowUp: result?.pregnancy_follow_up,
  })
  const alertTitle = deriveAlertTitle(log, graphs, summary.path, inputSnapshot, locale)
  const confirmation = confirmedText(locale)
  const confirmedFindings = summary.findings.filter(
    (finding) => finding.value === confirmation
      && !isHypertensionLabel(finding.label)
      && !titleContainsFinding(alertTitle, finding.label),
  )
  const detailedFindings = summary.findings.filter((finding) => finding.value !== confirmation)
  const recommendationAction = actionWithPresentation(actions) ?? actions.at(-1)
  const provenance = buildOrderProvenance(recommendationAction, references, graphs, locale)
  const medicationFollowUpMessage = deriveMedicationFollowUpMessage(actions, context, locale)
  const medicationReassessment = deriveMedicationReassessment(context, locale)
  const displayedOrders = withCurrentFollowUpRegimen(presentation.orders, context, locale)
  const careActions = deriveCareActions(
    presentation.recommendation, presentation.additionalActions, summary, context,
  )
  if (medicationFollowUpMessage && !careActions.includes(medicationFollowUpMessage)) {
    careActions.unshift(medicationFollowUpMessage)
  }
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    dialogRef.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return (
    <div className="modal-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div ref={dialogRef} className="modal-box cds-modal" role="dialog" aria-modal="true" aria-label={messages.recommendationTitle} tabIndex={-1}>
        <div className="modal-body cds-modal-body">
          <ClinicalSection title={messages.alertSection} className={`cds-alert-${summary.urgency}`}>
            <div className="cds-alert-row">
              <div className="cds-row-heading">
                <span className="cds-urgency-badge">{summary.urgencyLabel}</span>
                <strong>{alertTitle}</strong>
                {confirmedFindings.length > 0 && (
                  <span className="cds-confirmed-tags" aria-label={confirmation}>
                    {confirmedFindings.map((finding) => (
                      <span className="cds-confirmed-tag" key={finding.id} title={finding.treeName}>{finding.label}</span>
                    ))}
                  </span>
                )}
              </div>
              {!result && partial && <div className="cds-inner-row cds-error-copy">{partial.message}</div>}
              {result?.pregnancy_follow_up && (
                <div className="cds-inner-row cds-episode-row">
                  <span>{messages.pregnancyFollowUp}</span>
                  {result.pregnancy_follow_up.previous_visit_date && (
                    <strong>{messages.previousVisit}: {formatVisitDate(result.pregnancy_follow_up.previous_visit_date, locale)}</strong>
                  )}
                </div>
              )}
            </div>
          </ClinicalSection>

          <ClinicalSection title={messages.whyTitle}>
            {detailedFindings.length === 0 ? <p className="cds-empty">{messages.noEvidence}</p> : (
              <div className="cds-data-rows">
                {detailedFindings.map((finding) => (
                  <div className="cds-data-row" key={finding.id}>
                    <span>{finding.label}<small>{finding.treeName}</small></span>
                    <strong>{finding.value}</strong>
                  </div>
                ))}
              </div>
            )}
          </ClinicalSection>

          <ClinicalSection title={messages.recommendedAction}>
            {careActions.length === 0 && !summary.followUp && <p className="cds-empty">{messages.noAdditionalActions}</p>}
            {careActions.map((action) => (
              <div className="cds-inner-row cds-action-item" key={action}><span>{action}</span></div>
            ))}
            {medicationReassessment && (
              <div className="cds-inner-row cds-follow-up-row">
                <span>{locale === 'vi' ? 'Ngày tái đánh giá' : 'Reassessment date'}</span>
                <strong>{medicationReassessment.date}</strong>
              </div>
            )}
            {summary.followUp && (
              <div className="cds-inner-row cds-follow-up-row">
                <span>{messages.followUpTiming}</span><strong>{summary.followUp.timing}</strong>
                <small>{summary.followUp.reason} · {summary.followUp.source}</small>
              </div>
            )}
          </ClinicalSection>

          <ClinicalSection title={messages.recommendedOrders}>
            {displayedOrders.length === 0 ? <p className="cds-empty">{messages.noRecommendedOrders}</p> : (
              <div className="cds-order-rows">
                {displayedOrders.filter(isSingleMedicationOrder).length > 1 && (
                  <div className="cds-order-choice-hint">{messages.chooseOneMedicine}</div>
                )}
                {displayedOrders.map((order) => (
                  <RecommendedOrderCard
                    key={order.id} order={order} provenance={provenance} locale={locale}
                  />
                ))}
              </div>
            )}
          </ClinicalSection>

          <ClinicalSection
            title={messages.importantPath}
            subtitle={`${summary.path.length} · ${messages.pathSummary}`}
            className="cds-path-details"
            defaultOpen={false}
          >
            <ImportantDecisionPath steps={summary.path} emptyText={messages.noImportantPath} />
          </ClinicalSection>
        </div>
      </div>
    </div>
  )
}

export function TraversalResultModal({ locale, ...props }: TraversalResultModalProps) {
  if (!props.result && !props.partial) return null
  const resolvedLocale = locale
    ?? (document.documentElement.lang.toLowerCase().startsWith('vi') ? 'vi' : 'en')
  return <ResultDialog {...props} locale={resolvedLocale} />
}
