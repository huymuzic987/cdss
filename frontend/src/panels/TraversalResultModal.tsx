import { useEffect, useMemo, useRef, useState } from 'react'
import type { ApiErrorResponse, EvaluationResponse, TraversalTraceEntry } from '../api/types'
import { buildClinicalPresentation, type AcknowledgementOption, type RecommendedOrder } from './clinicalDecisionSupportAdapter'
import { getClinicalDecisionSupportMessages, type ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'

export type { OrderDecision, RecommendedOrder } from './clinicalDecisionSupportAdapter'

export interface AcknowledgementState { reason: string | null; otherText?: string }
export interface ClinicalDecisionSubmission {
  mode: 'place-orders' | 'acknowledge'
  orders: RecommendedOrder[]
  additionalActions: string[]
  acknowledgement: AcknowledgementState | null
}

interface TraversalResultModalProps {
  result: EvaluationResponse | null
  partial: ApiErrorResponse | null
  onClose: () => void
  onSubmit?: (submission: ClinicalDecisionSubmission) => void | Promise<void>
  locale?: ClinicalDecisionSupportLocale
}

function summariseCondition(definition: Record<string, unknown>): string {
  if ('all' in definition) return `ALL (${(definition.all as unknown[]).length} checks)`
  if ('any' in definition) return `ANY (${(definition.any as unknown[]).length} checks)`
  if ('not' in definition) return 'NOT (…)'
  if ('op' in definition) {
    const path = String(definition.path ?? definition.left ?? '?').replace(/^input\./, '')
    const right = 'value_from_path' in definition ? String(definition.value_from_path) : JSON.stringify(definition.value)
    return `${path} ${String(definition.op)} ${right}`
  }
  return JSON.stringify(definition).slice(0, 80)
}

function ConditionRow({ entry }: { entry: TraversalTraceEntry }) {
  const passed = entry.condition_result === true
  return (
    <div className="modal-condition-row">
      <span className={`modal-condition-badge ${passed ? 'passed' : 'failed'}`}>{passed ? '✓' : '×'}</span>
      <div className="modal-condition-info">
        <div className="modal-condition-node"><span className="modal-node-key">{entry.candidate_node_key ?? entry.node_key}</span></div>
        {entry.condition_definition && <div className="modal-condition-def">{summariseCondition(entry.condition_definition)}</div>}
      </div>
    </div>
  )
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

function OrderDecisionRow({ order, onDecision, locale }: {
  order: RecommendedOrder; onDecision: (decision: 'order' | 'do-not-order') => void; locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  return (
    <div className="cds-order-row">
      <div className="cds-order-copy">
        <div className="cds-order-name">{order.name}</div>
        {order.dose && <div className="cds-order-dose">{messages.startingDose}: {order.dose}</div>}
        {order.classLabel && <div className="cds-order-class">{order.classLabel}</div>}
      </div>
      <fieldset className="cds-decision-group">
        <legend className="sr-only">{order.name}</legend>
        <label className={order.decision === 'order' ? 'selected' : ''}>
          <input type="radio" name={`decision-${order.id}`} value="order" checked={order.decision === 'order'} onChange={() => onDecision('order')} />
          {messages.order}
        </label>
        <label className={order.decision === 'do-not-order' ? 'selected decline' : ''}>
          <input type="radio" name={`decision-${order.id}`} value="do-not-order" checked={order.decision === 'do-not-order'} onChange={() => onDecision('do-not-order')} />
          {messages.doNotOrder}
        </label>
      </fieldset>
    </div>
  )
}

function AcknowledgementReason({ options, value, error, onChange, locale }: {
  options: AcknowledgementOption[]; value: AcknowledgementState; error: string | null
  onChange: (value: AcknowledgementState) => void; locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const selectedOption = options.find((option) => option.id === value.reason)
  return (
    <section className="cds-section cds-acknowledgement" aria-labelledby="cds-ack-title">
      <h2 id="cds-ack-title">{messages.acknowledgementReason}</h2>
      <p className="cds-section-help">{messages.acknowledgementHelp}</p>
      <fieldset className="cds-ack-options" aria-describedby={error ? 'cds-ack-error' : undefined}>
        <legend className="sr-only">{messages.acknowledgementReason}</legend>
        {options.map((option) => (
          <label key={option.id}>
            <input type="radio" name="acknowledgement-reason" value={option.id} checked={value.reason === option.id} onChange={() => onChange({ reason: option.id })} />
            {option.label}
          </label>
        ))}
      </fieldset>
      {selectedOption?.requiresText && (
        <label className="cds-other-reason">
          <span>{messages.otherReason}</span>
          <input type="text" required value={value.otherText ?? ''} aria-invalid={Boolean(error)} onChange={(event) => onChange({ ...value, otherText: event.target.value })} />
        </label>
      )}
      {error && <div id="cds-ack-error" className="cds-validation-error" role="alert">{error}</div>}
    </section>
  )
}

function ResultDialog({ result, partial, onClose, onSubmit, locale }: Omit<TraversalResultModalProps, 'locale'> & { locale: ClinicalDecisionSupportLocale }) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const log = result?.traversal_log ?? partial?.partial_run_state?.traversal_log ?? []
  const context = result?.context ?? partial?.partial_run_state?.context ?? {}
  const presentation = useMemo(
    () => buildClinicalPresentation(
      result?.actions ?? partial?.partial_run_state?.actions ?? [],
      result?.input_snapshot ?? partial?.partial_run_state?.input_snapshot ?? {},
      result?.context ?? partial?.partial_run_state?.context ?? {},
      locale,
    ),
    [result, partial, locale],
  )
  const [orders, setOrders] = useState<RecommendedOrder[]>(presentation.orders)
  const [additionalActions, setAdditionalActions] = useState<string[]>([])
  const [acknowledgement, setAcknowledgement] = useState<AcknowledgementState>({ reason: null })
  const [acknowledgementRequested, setAcknowledgementRequested] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const dialogRef = useRef<HTMLDivElement>(null)
  const conditionEntries = log.filter((entry) => entry.event === 'candidate_evaluated' && entry.condition_result !== null)
  const enteredNodes = log.filter((entry) => entry.event === 'node_entered')
  const needsAcknowledgement = acknowledgementRequested || orders.some((order) => order.decision === 'do-not-order')
  const hasSelectedOrder = orders.some((order) => order.decision === 'order')

  useEffect(() => {
    dialogRef.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  function updateAction(id: string) {
    setAdditionalActions((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  }

  function validateAcknowledgement() {
    if (!acknowledgement.reason) { setValidationError(messages.reasonRequired); return false }
    const option = presentation.acknowledgementOptions.find((item) => item.id === acknowledgement.reason)
    if (option?.requiresText && !acknowledgement.otherText?.trim()) { setValidationError(messages.otherRequired); return false }
    setValidationError(null)
    return true
  }

  async function submit(mode: ClinicalDecisionSubmission['mode']) {
    const acknowledgementRequired = mode === 'acknowledge' || orders.some((order) => order.decision === 'do-not-order')
    if (acknowledgementRequired && !validateAcknowledgement()) { setAcknowledgementRequested(true); return }
    await onSubmit?.({
      mode, orders, additionalActions,
      acknowledgement: acknowledgementRequired ? { ...acknowledgement, otherText: acknowledgement.otherText?.trim() || undefined } : null,
    })
    onClose()
  }

  return (
    <div className="modal-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div ref={dialogRef} className="modal-box cds-modal" role="dialog" aria-modal="true" aria-labelledby="cds-modal-title" tabIndex={-1}>
        <header className="modal-header">
          <div>
            <div id="cds-modal-title" className="modal-header-title">{result ? messages.title : messages.incompleteTitle}</div>
            {!result && partial && <div className="modal-header-sub">{partial.message}</div>}
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label={messages.cancel}>×</button>
        </header>

        <div className="modal-body cds-modal-body">
          <section className="cds-alert" aria-labelledby="cds-alert-label">
            <div id="cds-alert-label" className="cds-alert-label">{messages.alertLabel}</div>
            <p>{presentation.alert}</p>
          </section>

          <TriggerEvidence items={presentation.evidence} title={messages.whyTitle} emptyText={messages.noEvidence} />

          <section className="cds-section cds-recommendation" aria-labelledby="cds-recommendation-title">
            <h2 id="cds-recommendation-title">{messages.recommendedAction}</h2>
            <p className="cds-recommendation-copy">{presentation.recommendation}</p>
            {presentation.recommendationSecondary && <p className="cds-bilingual-copy">{presentation.recommendationSecondary}</p>}
            <div className="cds-recommendation-meta">
              <button type="button" className="cds-link-button" onClick={() => setDetailsOpen(true)}>{messages.viewGuideline}</button>
              {presentation.recommendationStrength && <span>{messages.recommendationStrength}: {presentation.recommendationStrength}</span>}
              {presentation.evidenceLevel && <span>{messages.evidenceLevel}: {presentation.evidenceLevel}</span>}
            </div>
          </section>

          <section className="cds-section cds-orders" aria-labelledby="cds-orders-title">
            <h2 id="cds-orders-title">{messages.recommendedOrders}</h2>
            {orders.length === 0 ? <p className="cds-empty">{messages.noOrders}</p> : orders.map((order) => (
              <OrderDecisionRow key={order.id} order={order} locale={locale} onDecision={(decision) => {
                setOrders((current) => current.map((item) => item.id === order.id ? { ...item, decision } : item))
                setValidationError(null)
              }} />
            ))}
          </section>

          <section className="cds-additional-actions" aria-labelledby="cds-additional-title">
            <h2 id="cds-additional-title">{messages.additionalActions}</h2>
            {presentation.additionalActions.length === 0 ? <p className="cds-empty">{messages.noAdditionalActions}</p> : presentation.additionalActions.map((action) => (
              <label key={action.id}>
                <input type="checkbox" checked={additionalActions.includes(action.id)} onChange={() => updateAction(action.id)} />
                {action.label}
              </label>
            ))}
          </section>

          {needsAcknowledgement && <AcknowledgementReason options={presentation.acknowledgementOptions} value={acknowledgement} error={validationError} locale={locale} onChange={(value) => { setAcknowledgement(value); setValidationError(null) }} />}

          <details className="modal-debug" open={detailsOpen} onToggle={(event) => setDetailsOpen(event.currentTarget.open)}>
            <summary>{messages.clinicalDetails}</summary>
            <div className="modal-clinical-details">
              {presentation.clinicalDetails.length > 0 && <dl className="cds-evidence-grid">
                {presentation.clinicalDetails.map((item) => <div className="cds-evidence-row" key={item.id}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
              </dl>}
              {presentation.guidelineReferences.length > 0 && <section className="modal-clinical-section">
                <div className="modal-clinical-section-title">{messages.viewGuideline}</div>
                {presentation.guidelineReferences.map((reference) => <div className="cds-reference" key={reference.id}>{reference.title}{reference.locator ? ` — ${reference.locator}` : ''}</div>)}
              </section>}
              <section className="modal-clinical-section">
                <div className="modal-clinical-section-title">{messages.fullDecisionPath} ({enteredNodes.length})</div>
                <div className="modal-path">{enteredNodes.map((entry, index) => <div className="modal-path-step" key={`${entry.tree_key}-${entry.node_key}-${index}`}>
                  <span className="modal-path-num">{index + 1}</span><span className="modal-path-tree">{entry.tree_key}</span><span className="modal-path-node">{entry.node_key}</span>
                </div>)}</div>
              </section>
              {!result && Object.keys(context).length > 0 && <section className="modal-clinical-section">
                <div className="modal-clinical-section-title">{messages.derivedContext}</div><pre className="modal-json">{JSON.stringify(context, null, 2)}</pre>
              </section>}
              {!result && conditionEntries.length > 0 && <section className="modal-clinical-section">
                <div className="modal-clinical-section-title">{messages.conditionChecks}</div>{conditionEntries.map((entry, index) => <ConditionRow entry={entry} key={index} />)}
              </section>}
            </div>
          </details>
        </div>

        <footer className="modal-footer cds-modal-footer">
          <button type="button" className="cds-button secondary" onClick={onClose}>{messages.cancel}</button>
          <button type="button" className="cds-button neutral" onClick={() => { setAcknowledgementRequested(true); void submit('acknowledge') }}>{messages.acknowledge}</button>
          <button type="button" className="cds-button primary" disabled={!hasSelectedOrder} onClick={() => void submit('place-orders')}>{messages.acceptOrders}</button>
        </footer>
      </div>
    </div>
  )
}

export function TraversalResultModal({ locale, ...props }: TraversalResultModalProps) {
  if (!props.result && !props.partial) return null
  const resolvedLocale = locale ?? (document.documentElement.lang.toLowerCase().startsWith('vi') ? 'vi' : 'en')
  return <ResultDialog {...props} locale={resolvedLocale} />
}
