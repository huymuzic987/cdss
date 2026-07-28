import { useEffect, useMemo, useRef, useState } from 'react'
import type { ApiErrorResponse, EvaluationResponse, TraversalTraceEntry } from '../api/types'
import { buildClinicalPresentation, type RecommendedDrugClass, type RecommendedOrder } from './clinicalDecisionSupportAdapter'
import { getClinicalDecisionSupportMessages, type ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'

export type { RecommendedOrder } from './clinicalDecisionSupportAdapter'

interface TraversalResultModalProps {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  onClose: () => void
  locale?: ClinicalDecisionSupportLocale
}

const TECHNICAL_NODE_TOKENS = new Set([
  'ACTION', 'CHECK', 'COND', 'CONDITION', 'END', 'GLOBAL', 'INF', 'INFERENCE', 'LINK', 'NODE', 'START',
])

function readableIdentifier(value: string): string {
  const words = value
    .replace(/^T\d+[A-Z]?(?:_|-)/i, '')
    .split(/[_-]+/)
    .filter((word) => word && !TECHNICAL_NODE_TOKENS.has(word.toUpperCase()))
    .map((word) => word.toLowerCase())
  if (words.length === 0) return 'Clinical assessment'
  const text = words.join(' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function readablePathStep(
  entry: TraversalTraceEntry,
  actions: EvaluationResponse['actions'],
  locale: ClinicalDecisionSupportLocale,
): string {
  const action = actions.find((item) => item.tree_key === entry.tree_key && item.node_key === entry.node_key)
  if (action) return locale === 'vi' ? action.text_vi || action.text_en : action.text_en || action.text_vi
  const subject = readableIdentifier(entry.node_key)
  if (entry.node_type === 'START') return locale === 'vi' ? 'Bắt đầu đánh giá lâm sàng' : 'Begin clinical assessment'
  if (entry.node_type === 'CONDITION') return locale === 'vi' ? `Đánh giá: ${subject}` : `Assess: ${subject}`
  if (entry.node_type === 'INFERENCE') return locale === 'vi' ? `Xác định: ${subject}` : `Determine: ${subject}`
  if (entry.node_type === 'LINK') return locale === 'vi' ? `Tiếp tục đánh giá: ${subject}` : `Continue assessment: ${subject}`
  return subject
}

function TriggerEvidence({ items, title, emptyText }: {
  items: { id: string; label: string; value: string }[]; title: string; emptyText: string
}) {
  return (
    <section className="cds-section cds-evidence" aria-labelledby="cds-evidence-title">
      <h2 id="cds-evidence-title">{title}</h2>
      {items.length === 0 ? <p className="cds-empty">{emptyText}</p> : (
        <dl className="cds-evidence-grid">
          {items.map((item) => (
            <div className="cds-evidence-row" key={item.id}><dt>{item.label}</dt><dd>{item.value}</dd></div>
          ))}
        </dl>
      )}
    </section>
  )
}

function DrugClassDetails({ drugClass, orderId, locale }: {
  drugClass: RecommendedDrugClass; orderId: string; locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const [open, setOpen] = useState(false)
  const tooltipId = `cds-class-${orderId}-${drugClass.code}`.replace(/[^a-zA-Z0-9_-]/g, '-')
  return (
    <div
      className="cds-drug-class"
      tabIndex={0}
      aria-describedby={open ? tooltipId : undefined}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span className="cds-drug-class-label">{drugClass.label}</span>
      {open && <div className="cds-drug-tooltip" id={tooltipId} role="tooltip">
        <div className="cds-drug-tooltip-title">{drugClass.label}{drugClass.doseLabel ? ` · ${drugClass.doseLabel}` : ''}</div>
        {drugClass.medicines.length === 0 ? <p className="cds-empty">{messages.noMedicines}</p> : (
          <table>
            <thead><tr><th>{messages.medicineName}</th><th>{messages.dose}</th></tr></thead>
            <tbody>{drugClass.medicines.map((medicine) => (
              <tr key={medicine.id}>
                <td><strong>{medicine.name}</strong>{medicine.subgroup && <small>{medicine.subgroup}</small>}</td>
                <td>{medicine.dose}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>}
    </div>
  )
}

function RecommendedOrderCard({ order, locale }: {
  order: RecommendedOrder; locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const normalizedName = order.name.toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, '')
  const normalizedClass = order.classLabel?.toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, '')
  const showClass = order.classLabel && normalizedClass !== normalizedName
  return (
    <div className="cds-order-row">
      <div className="cds-order-copy">
        {order.drugClasses?.length ? (
          <div className="cds-order-name cds-class-combination">
            {order.drugClasses.map((drugClass, index) => <div className="cds-class-part" key={drugClass.code}>
              {index > 0 && <span className="cds-class-separator"> + </span>}
              <DrugClassDetails drugClass={drugClass} orderId={order.id} locale={locale} />
            </div>)}
          </div>
        ) : <>
          <div className="cds-order-name">{order.name}</div>
          {order.dose && <div className="cds-order-dose">{messages.startingDose}: {order.dose}</div>}
          {showClass && <div className="cds-order-class">{order.classLabel}</div>}
        </>}
      </div>
    </div>
  )
}

function ResultDialog({ result, partial, onClose, locale }: Omit<TraversalResultModalProps, 'locale'> & { locale: ClinicalDecisionSupportLocale }) {
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
  const orders = presentation.orders
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
          <button type="button" className="modal-close" onClick={onClose} aria-label={messages.cancel}>×</button>
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

          {orders.length > 0 && <section className="cds-section cds-orders" aria-label={messages.recommendedOrders}>
            {orders.map((order) => <RecommendedOrderCard key={order.id} order={order} locale={locale} />)}
          </section>}

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
