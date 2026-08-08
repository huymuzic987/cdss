import type { ApiErrorResponse, EvaluationResponse } from '../api/types'
import type { RecommendedOrder } from './clinicalDecisionSupportAdapter'
import { getClinicalDecisionSupportMessages, type ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'
import { ClinicalSection } from './clinicalResult/ClinicalSection'
import { formatVisitDate } from './clinicalResult/criticalFindingFormat'
import type { CriticalFinding, CriticalSummary } from './clinicalResult/criticalSummaryTypes'
import { ImportantDecisionPath } from './clinicalResult/ImportantDecisionPath'
import { RecommendedOrderCard } from './clinicalResult/RecommendedOrderCard'
import { RegimenDisplay, RegimenPathDisplay } from './clinicalResult/RegimenDisplay'
import type { OrderProvenance } from './clinicalResult/RecommendedOrderCard'
import type { ClinicalPresentation } from './clinicalPresentation/types'
import { isSingleMedicationOrder } from './clinicalResult/orderClassification'

interface TraversalResultBodyProps {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  messages: ReturnType<typeof getClinicalDecisionSupportMessages>
  summary: CriticalSummary
  alertTitle: string
  confirmation: string
  confirmedFindings: CriticalFinding[]
  detailedFindings: CriticalFinding[]
  careActions: string[]
  medicationReassessment: { date: string } | null
  displayedOrders: RecommendedOrder[]
  provenance: OrderProvenance
  presentation: ClinicalPresentation
  references: EvaluationResponse['references']
  locale: ClinicalDecisionSupportLocale
}

export function TraversalResultBody({ result, partial, messages, summary, alertTitle, confirmation, confirmedFindings, detailedFindings, careActions, medicationReassessment, displayedOrders, provenance, presentation, references, locale }: TraversalResultBodyProps) {
  return <div className="modal-body cds-modal-body">
    <ClinicalSection title={messages.alertSection} className={`cds-alert-${summary.urgency}`}><div className="cds-alert-row"><div className="cds-row-heading"><span className="cds-urgency-badge">{summary.urgencyLabel}</span><strong>{alertTitle}</strong>{confirmedFindings.length > 0 && <span className="cds-confirmed-tags" aria-label={confirmation}>{confirmedFindings.map((finding) => <span className="cds-confirmed-tag" key={finding.id} title={finding.treeName}>{finding.label}</span>)}</span>}</div>{!result && partial && <div className="cds-inner-row cds-error-copy">{partial.message}</div>}{result?.pregnancy_follow_up && <div className="cds-inner-row cds-episode-row"><span>{messages.pregnancyFollowUp}</span>{result.pregnancy_follow_up.previous_visit_date && <strong>{messages.previousVisit}: {formatVisitDate(result.pregnancy_follow_up.previous_visit_date, locale)}</strong>}</div>}</div></ClinicalSection>
    <ClinicalSection title={messages.whyTitle}>{detailedFindings.length === 0 ? <p className="cds-empty">{messages.noEvidence}</p> : <div className="cds-data-rows">{detailedFindings.map((finding) => <div className="cds-data-row" key={finding.id}><span>{finding.label}<small>{finding.treeName}</small></span><strong>{finding.value}</strong></div>)}</div>}</ClinicalSection>
    <ClinicalSection title={messages.recommendedAction}>{careActions.length === 0 && !summary.followUp && <p className="cds-empty">{messages.noAdditionalActions}</p>}{careActions.map((action) => <div className="cds-inner-row cds-action-item" key={action}><span>{action}</span></div>)}{medicationReassessment && <div className="cds-inner-row cds-follow-up-row"><span>{locale === 'vi' ? 'Ngày tái đánh giá' : 'Reassessment date'}</span><strong>{medicationReassessment.date}</strong></div>}{summary.followUp && <div className="cds-inner-row cds-follow-up-row"><span>{messages.followUpTiming}</span><strong>{summary.followUp.timing}</strong><small>{summary.followUp.reason} · {summary.followUp.source}</small></div>}</ClinicalSection>
    {presentation.regimenOptions.length > 0 && <RegimenDisplay presentation={presentation} references={references} locale={locale} />}
    {(displayedOrders.length > 0 || presentation.regimenOptions.length === 0) && <ClinicalSection title={messages.recommendedOrders}>{displayedOrders.length === 0 ? <p className="cds-empty">{messages.noRecommendedOrders}</p> : <div className="cds-order-rows">{displayedOrders.filter(isSingleMedicationOrder).length > 1 && <div className="cds-order-choice-hint">{messages.chooseOneMedicine}</div>}{displayedOrders.map((order) => <RecommendedOrderCard key={order.id} order={order} provenance={provenance} locale={locale} />)}</div>}</ClinicalSection>}
    <ClinicalSection title={messages.importantPath} subtitle={`${summary.path.length} · ${messages.pathSummary}`} className="cds-path-details" defaultOpen={false}><ImportantDecisionPath steps={summary.path} emptyText={messages.noImportantPath} /><RegimenPathDisplay presentation={presentation} locale={locale} /></ClinicalSection>
  </div>
}
