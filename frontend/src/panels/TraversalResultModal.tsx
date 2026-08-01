import { useEffect, useRef } from 'react'
import type {
  ApiErrorResponse,
  EvaluationResponse,
  ExecutedAction,
  TreeGraphResponse,
} from '../api/types'
import { buildClinicalPresentation } from './clinicalDecisionSupportAdapter'
import {
  getClinicalDecisionSupportMessages,
  type ClinicalDecisionSupportLocale,
} from './clinicalDecisionSupportMessages'
import { deriveCriticalSummary } from './clinicalResult/criticalSummary'
import { formatVisitDate } from './clinicalResult/criticalFindingFormat'
import { deriveCareActions } from './clinicalResult/careActions'
import { ClinicalSection } from './clinicalResult/ClinicalSection'
import { readableIdentifier } from './clinicalResult/decisionPath'
import { ImportantDecisionPath } from './clinicalResult/ImportantDecisionPath'
import {
  RecommendedOrderCard,
  type OrderProvenance,
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
  const actions = result?.actions ?? state?.actions ?? []
  const context = result?.context ?? state?.context ?? {}
  const log = result?.traversal_log ?? state?.traversal_log ?? []
  const references = result?.references ?? state?.references ?? []
  const presentation = buildClinicalPresentation(
    actions,
    result?.input_snapshot ?? state?.input_snapshot ?? {},
    context,
    locale,
  )
  const summary = deriveCriticalSummary({
    log, actions, context, graphs, locale,
    pregnancyFollowUp: result?.pregnancy_follow_up,
  })
  const dialogRef = useRef<HTMLDivElement>(null), recommendationAction = actionWithPresentation(actions) ?? actions.at(-1)
  const provenance = orderProvenance(recommendationAction, references, graphs, locale), alertTitle = patientAlert(
    presentation.alert, summary.findings, recommendationAction, partial, locale,
  ), careActions = deriveCareActions(
    presentation.recommendation, presentation.additionalActions, summary, context,
  )

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
            </div>
            {careActions[0] && summary.urgency !== 'routine' && (
              <div className="cds-alert-action">
                <span>{messages.actionNow}</span><strong>{careActions[0]}</strong>
              </div>
            )}
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
            {summary.findings.length === 0 ? <p className="cds-empty">{messages.noEvidence}</p> : (
              <div className="cds-data-rows">
                {summary.findings.map((finding) => (
                  <div className="cds-data-row" key={finding.id}>
                    <span>{finding.label}<small>{finding.treeName}</small></span>
                    <strong>{finding.value}</strong>
                  </div>
                ))}
              </div>
            )}
          </ClinicalSection>

          <ClinicalSection title={messages.recommendedAction}>
            {careActions.length === 0 && !summary.followUp && (
              <p className="cds-empty">{messages.noAdditionalActions}</p>
            )}
            {careActions.map((action) => (
              <div className="cds-inner-row cds-action-item" key={action}>
                <span aria-hidden="true">→</span><span>{action}</span>
              </div>
            ))}
            {summary.followUp && (
              <div className="cds-inner-row cds-follow-up-row">
                <span>{messages.followUpTiming}</span>
                <strong>{summary.followUp.timing}</strong>
                <small>{summary.followUp.reason} · {summary.followUp.source}</small>
              </div>
            )}
          </ClinicalSection>

          <ClinicalSection title={messages.recommendedOrders}>
            {presentation.orders.length === 0 ? <p className="cds-empty">{messages.noRecommendedOrders}</p> : (
              <div className="cds-order-rows">
                {presentation.orders.map((order) => (
                  <RecommendedOrderCard
                    key={order.id}
                    order={order}
                    provenance={provenance}
                    locale={locale}
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

function actionWithPresentation(actions: ExecutedAction[]): ExecutedAction | undefined {
  return [...actions].reverse().find((action) => {
    const value = action.payload.presentation
    return typeof value === 'object' && value !== null && !Array.isArray(value)
  })
}

function orderProvenance(
  action: ExecutedAction | undefined,
  references: EvaluationResponse['references'],
  graphs: Record<string, TreeGraphResponse>,
  locale: ClinicalDecisionSupportLocale,
): OrderProvenance {
  if (!action) return { nodeLabel: 'Clinical recommendation', nodeKey: 'N/A', treeName: 'CDSS', references: [] }
  const graph = graphs[action.tree_key]
  const node = graph?.nodes.find((item) => item.node_key === action.node_key)
  const nodeLabel = locale === 'vi'
    ? node?.text_vi || action.text_vi || node?.text_en || action.text_en
    : node?.text_en || action.text_en || node?.text_vi || action.text_vi
  const treeName = graph
    ? (locale === 'vi' ? graph.tree.name_vi || graph.tree.name_en : graph.tree.name_en || graph.tree.name_vi)
    : readableIdentifier(action.tree_key)
  return {
    nodeLabel,
    nodeKey: action.node_key,
    treeName,
    references: references.filter(
      (reference) => reference.tree_key === action.tree_key && reference.node_key === action.node_key,
    ),
  }
}

function patientAlert(
  alert: string,
  findings: ReturnType<typeof deriveCriticalSummary>['findings'],
  action: ExecutedAction | undefined,
  partial: ApiErrorResponse | null,
  locale: ClinicalDecisionSupportLocale,
): string {
  const unusable = /clinical decision support|support recommendation|maintain regimen|recorded regimen|pregnancy safety|combination \(/i
  if (alert && alert.length <= 120 && !unusable.test(alert)) return alert
  const finding = findings[0]
  if (finding) return `${finding.label}: ${finding.value}`
  const actionText = action ? (locale === 'vi' ? action.text_vi || action.text_en : action.text_en || action.text_vi) : ''
  if (actionText && actionText.length <= 120 && !unusable.test(actionText)) return actionText
  return partial?.message || (locale === 'vi' ? 'Cần xem xét ngay dữ kiện lâm sàng quan trọng' : 'Important clinical findings require review')
}

export function TraversalResultModal({ locale, ...props }: TraversalResultModalProps) {
  if (!props.result && !props.partial) return null
  const resolvedLocale = locale
    ?? (document.documentElement.lang.toLowerCase().startsWith('vi') ? 'vi' : 'en')
  return <ResultDialog {...props} locale={resolvedLocale} />
}
