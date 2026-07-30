import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown, TriangleAlert } from 'lucide-react'
import type {
  ApiErrorResponse,
  EvaluationResponse,
  TraversalTraceEntry,
} from '../api/types'
import {
  buildClinicalPresentation,
  type GuidelineReference,
  type RecommendedDrugClass,
  type RecommendedOrder,
} from './clinicalDecisionSupportAdapter'
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

function buildAlertSummary(
  summary: string,
  evidence: { id: string; value: string }[],
  locale: ClinicalDecisionSupportLocale,
  fallback: string,
): string {
  const patientPrefix = locale === 'vi' ? 'Bệnh nhân có' : 'Patient has'
  const prefixPattern = /^(?:Patient\s+has|Bệnh\s+nhân\s+có)\s*/iu
  const excludedClausePattern = /(?:\b(?:BP|SBP|DBP|HATT|HATTr|mmHg)\b|Huyết\s*áp|Grade\s*\d+\s+hypertension|Tăng\s+huyết\s+áp\s+độ|treatment|điều\s+trị)/iu
  const findings = summary
    .replace(prefixPattern, '')
    .split(/\s*;\s*/)
    .map((part) => physicianReadableFinding(part.trim().replace(/[.;]\s*$/, '')))
    .filter((part) => part && !excludedClausePattern.test(part))
  const uniqueFindings = Array.from(new Map(
    findings.map((finding) => [finding.toLocaleLowerCase(), finding]),
  ).values())
  if (uniqueFindings.length > 0) return `${patientPrefix} ${uniqueFindings.join('; ')}`

  const comorbidities = evidence.find((item) => item.id === 'clinical-comorbidities')?.value.trim()
  return comorbidities
    ? `${patientPrefix} ${physicianReadableFinding(comorbidities)}`
    : fallback
}

function physicianReadableFinding(value: string): string {
  const withoutTechnicalPrefix = value.replace(/^(?:has|is)_/i, '')
  if (!withoutTechnicalPrefix.includes('_')) return withoutTechnicalPrefix
  const words = withoutTechnicalPrefix.replaceAll('_', ' ').replace(/\s+/g, ' ').trim().toLowerCase()
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : ''
}

function AlertSummary({ text, label }: { text: string; label: string }) {
  return (
    <section className="cds-alert-summary" aria-label={label} aria-live="polite">
      <TriangleAlert className="cds-alert-summary-icon" size={20} strokeWidth={2.2} aria-hidden="true" />
      <span className="cds-alert-summary-text">{text}</span>
    </section>
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
            <div
              className={`cds-evidence-item${item.id === 'clinical-patient-context' ? ' cds-evidence-item-context' : ''}`}
              key={item.id}
            >
              {item.id === 'clinical-patient-context'
                ? <><dt className="sr-only">{item.label}</dt><dd>{item.value}</dd></>
                : <><dt>{item.label}</dt><dd>{item.value}</dd></>}
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}

function DrugClassDetails({ drugClass, orderId, references, locale }: {
  drugClass: RecommendedDrugClass
  orderId: string
  references: GuidelineReference[]
  locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const anchorRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState<{
    top?: number; bottom?: number; left: number; width: number; maxHeight: number
  } | null>(null)
  const tooltipId = `cds-class-${orderId}-${drugClass.code}`.replace(/[^a-zA-Z0-9_-]/g, '-')

  useLayoutEffect(() => {
    if (!open) return
    function updatePosition() {
      const anchor = anchorRef.current
      if (!anchor) return
      const rect = anchor.getBoundingClientRect()
      const margin = 12
      const gap = 8
      const width = Math.min(720, window.innerWidth - margin * 2)
      const left = Math.min(
        Math.max(margin, rect.left),
        Math.max(margin, window.innerWidth - width - margin),
      )
      const below = window.innerHeight - rect.bottom - margin - gap
      const above = rect.top - margin - gap
      const placeBelow = below >= 320 || below >= above
      const maxHeight = Math.max(180, placeBelow ? below : above)
      setPosition(placeBelow
        ? { top: rect.bottom + gap, left, width, maxHeight }
        : { bottom: window.innerHeight - rect.top + gap, left, width, maxHeight })
    }
    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function closeOnOutsidePointer(event: PointerEvent) {
      const target = event.target
      if (!(target instanceof Node)) return
      if (anchorRef.current?.contains(target) || popoverRef.current?.contains(target)) return
      setOpen(false)
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      setOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsidePointer)
    document.addEventListener('keydown', closeOnEscape, true)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer)
      document.removeEventListener('keydown', closeOnEscape, true)
    }
  }, [open])
  const guidelineSources = Array.from(new Set(
    references.map((reference) => reference.sourceTitle.trim()).filter(Boolean),
  ))
  const guidelineSections = Array.from(new Set(
    references
      .map((reference) => (reference.locator || reference.sectionPath).trim())
      .filter(Boolean),
  ))

  const popover = open && position && createPortal(
    <div
      ref={popoverRef}
      className="cds-drug-tooltip"
      id={tooltipId}
      role="tooltip"
      style={position}
    >
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
      {(guidelineSources.length > 0 || guidelineSections.length > 0) && <div className="cds-drug-guideline">
        {guidelineSources.length > 0 && (
          <div><span>{messages.guidelineSource}</span>{guidelineSources.join('; ')}</div>
        )}
        {guidelineSections.length > 0 && (
          <div><span>{messages.section}</span>{guidelineSections.join('; ')}</div>
        )}
      </div>}
    </div>,
    document.body,
  )

  return (
    <>
      <button
        ref={anchorRef}
        type="button"
        className="cds-drug-class"
        aria-expanded={open}
        aria-describedby={open ? tooltipId : undefined}
        onClick={() => setOpen((current) => !current)}
      >
        <span className="cds-drug-class-label">
          <span>{drugClass.label}</span>
          <ChevronDown className="cds-drug-class-icon" size={14} aria-hidden="true" />
        </span>
      </button>
      {popover}
    </>
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
              <DrugClassDetails
                drugClass={drugClass}
                orderId={order.id}
                references={order.strategyReferences}
                locale={locale}
              />
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
  const alertSummary = buildAlertSummary(
    presentation.alertSummary,
    presentation.evidence,
    locale,
    messages.genericAlertSummary,
  )
  const dialogRef = useRef<HTMLDivElement>(null)
  const actions = result?.actions ?? partial?.partial_run_state?.actions ?? []
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
          <AlertSummary text={alertSummary} label={messages.alertSummary} />

          <TriggerEvidence items={presentation.evidence} title={messages.whyTitle} emptyText={messages.noEvidence} />

          <section className="cds-section cds-recommendation" aria-labelledby="cds-recommendation-title">
            <h2 id="cds-recommendation-title">{messages.recommendedAction}</h2>
            <p className="cds-recommendation-copy">{presentation.recommendation}</p>
            <div className="cds-recommendation-meta">
              {presentation.recommendationStrength && <span>{messages.recommendationStrength}: {presentation.recommendationStrength}</span>}
              {presentation.evidenceLevel && <span>{messages.evidenceLevel}: {presentation.evidenceLevel}</span>}
            </div>
            {orders.length > 0 && <div className="cds-orders" aria-label={messages.recommendedOrders}>
              {orders.map((order) => <RecommendedOrderCard key={order.id} order={order} locale={locale} />)}
            </div>}
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
                  <span className="modal-path-node">{readablePathStep(entry, actions, locale)}</span>
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
