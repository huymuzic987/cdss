import { useEffect, useMemo, useRef } from 'react'
import type { ApiErrorResponse, EvaluationResponse } from '../api/types'
import { buildClinicalPresentation } from './clinicalDecisionSupportAdapter'
import { getClinicalDecisionSupportMessages, type ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'
import { readableIdentifier, readablePathStep } from './clinicalResult/decisionPath'
import { RecommendedOrderCard } from './clinicalResult/RecommendedOrderCard'
import { TriggerEvidence } from './clinicalResult/TriggerEvidence'

export type { RecommendedOrder } from './clinicalDecisionSupportAdapter'

interface TraversalResultModalProps {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  onClose: () => void
  locale?: ClinicalDecisionSupportLocale
}

function ResultDialog({ result, partial, onClose, locale }: Omit<TraversalResultModalProps, 'locale'> & {
  locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const log = result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []
  const presentation = useMemo(
    () => buildClinicalPresentation(
      result?.actions ?? partial?.partial_run_state?.actions ?? [],
      result?.input_snapshot ?? partial?.partial_run_state?.input_snapshot ?? {},
      result?.context ?? partial?.partial_run_state?.context ?? {},
      locale,
    ),
    [result, partial, locale],
  )
  const dialogRef = useRef<HTMLDivElement>(null)
  const enteredNodes = log.filter((entry) => entry.event === 'node_entered')

  useEffect(() => {
    dialogRef.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return (
    <div className="modal-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div ref={dialogRef} className="modal-box cds-modal" role="dialog" aria-modal="true" aria-labelledby="cds-modal-title" tabIndex={-1}>
        <header className="modal-header">
          <div>
            <div id="cds-modal-title" className="modal-header-title">{messages.recommendationTitle}</div>
            {!result && partial && <div className="modal-header-sub">{partial.message}</div>}
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label={messages.cancel}>Ã—</button>
        </header>
        <div className="modal-body cds-modal-body">
          <TriggerEvidence items={presentation.evidence} title={messages.whyTitle} emptyText={messages.noEvidence} />
          <section className="cds-section cds-recommendation" aria-labelledby="cds-recommendation-title">
            <h2 id="cds-recommendation-title">{messages.recommendedAction}</h2>
            <p className="cds-recommendation-copy">{presentation.recommendation}</p>
            {presentation.recommendationSecondary && <p className="cds-bilingual-copy">{presentation.recommendationSecondary}</p>}
            <div className="cds-recommendation-meta">
              {presentation.recommendationStrength && <span>{messages.recommendationStrength}: {presentation.recommendationStrength}</span>}
              {presentation.evidenceLevel && <span>{messages.evidenceLevel}: {presentation.evidenceLevel}</span>}
            </div>
          </section>
          {presentation.orders.length > 0 && (
            <section className="cds-section cds-orders" aria-label={messages.recommendedOrders}>
              {presentation.orders.map((order) => <RecommendedOrderCard key={order.id} order={order} locale={locale} />)}
            </section>
          )}
          <section className="cds-additional-actions" aria-labelledby="cds-additional-title">
            <h2 id="cds-additional-title">{messages.additionalActions}</h2>
            {presentation.additionalActions.length === 0 ? <p className="cds-empty">{messages.noAdditionalActions}</p> : (
              <ul>{presentation.additionalActions.map((action) => <li key={action.id}>{action.label}</li>)}</ul>
            )}
          </section>
          <details className="modal-debug cds-decision-path">
            <summary>{messages.fullDecisionPath}</summary>
            <div className="modal-path">{enteredNodes.map((entry, index) => {
              const metadata = result?.tree_metadata.find((tree) => tree.tree_key === entry.tree_key)
              const treeName = metadata
                ? (locale === 'vi' ? metadata.name_vi || metadata.name_en : metadata.name_en || metadata.name_vi)
                : readableIdentifier(entry.tree_key)
              return <div className="modal-path-step" key={`${entry.tree_key}-${entry.node_key}-${index}`}>
                <span className="modal-path-num">{index + 1}</span>
                <span className="modal-path-copy">
                  <span className="modal-path-node">{readablePathStep(entry, result?.actions ?? partial?.partial_run_state?.actions ?? [], locale)}</span>
                  <span className="modal-path-tree">{treeName}</span>
                </span>
              </div>
            })}</div>
          </details>
        </div>
      </div>
    </div>
  )
}

export function TraversalResultModal({ locale, ...props }: TraversalResultModalProps) {
  if (!props.result && !props.partial) return null
  const resolvedLocale = locale ?? (document.documentElement.lang.toLowerCase().startsWith('vi') ? 'vi' : 'en')
  return <ResultDialog {...props} locale={resolvedLocale} />
}
