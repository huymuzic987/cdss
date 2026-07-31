import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ExecutedReference } from '../../api/types'
import type { RecommendedOrder } from '../clinicalDecisionSupportAdapter'
import {
  getClinicalDecisionSupportMessages,
  type ClinicalDecisionSupportLocale,
} from '../clinicalDecisionSupportMessages'

export interface OrderProvenance {
  nodeLabel: string
  nodeKey: string
  treeName: string
  references: ExecutedReference[]
}

export function RecommendedOrderCard({ order, provenance, locale }: {
  order: RecommendedOrder
  provenance: OrderProvenance
  locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const anchorRef = useRef<HTMLSpanElement>(null)
  const openTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState<{
    top?: number; bottom?: number; left: number; width: number; maxHeight: number
  } | null>(null)
  const tooltipId = `cds-order-${order.id}`.replace(/[^a-zA-Z0-9_-]/g, '-')
  const isAbcdCombination = (order.drugClasses?.length ?? 0) > 1
    && order.drugClasses!.every((item) => /^[ABCD]$/.test(item.code))
  const combinationDose = order.drugClasses?.[0]?.doseLabel || order.dose

  function cancelTimers() {
    if (openTimer.current !== null) clearTimeout(openTimer.current)
    if (closeTimer.current !== null) clearTimeout(closeTimer.current)
    openTimer.current = null
    closeTimer.current = null
  }
  function scheduleOpen() {
    cancelTimers()
    openTimer.current = setTimeout(() => setOpen(true), 90)
  }
  function scheduleClose() {
    cancelTimers()
    closeTimer.current = setTimeout(() => setOpen(false), 240)
  }

  useLayoutEffect(() => {
    if (!open) return
    function updatePosition() {
      if (!anchorRef.current) return
      const rect = anchorRef.current.getBoundingClientRect()
      const margin = 12, gap = 8
      const width = Math.min(760, window.innerWidth - margin * 2)
      const left = Math.min(Math.max(margin, rect.right - width), window.innerWidth - width - margin)
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

  useEffect(() => () => cancelTimers(), [])

  const tooltip = isAbcdCombination && open && position && createPortal(
    <div
      id={tooltipId}
      className="cds-drug-tooltip"
      role="tooltip"
      style={position}
      onMouseEnter={cancelTimers}
      onMouseLeave={scheduleClose}
    >
      <div className="cds-tooltip-header">
        <strong>{messages.combinationTherapy}</strong>
        {combinationDose && <span>{messages.startingDose}: {combinationDose}</span>}
      </div>
      <div className="cds-tooltip-grid">
        {order.drugClasses?.map((drugClass) => (
          <div className="cds-tooltip-drug-class" key={drugClass.code}>
            <h4>{drugClass.label}{drugClass.doseLabel ? ` · ${drugClass.doseLabel}` : ''}</h4>
            {drugClass.medicines.length === 0 ? <p className="cds-empty">{messages.noMedicines}</p> : (
              <table><tbody>{drugClass.medicines.map((medicine) => (
                <tr key={medicine.id}>
                  <td><strong>{medicine.name}</strong>{medicine.subgroup && <small>{medicine.subgroup}</small>}</td>
                  <td>{medicine.dose}</td>
                </tr>
              ))}</tbody></table>
            )}
          </div>
        ))}
      </div>
      <div className="cds-tooltip-reference-row">
          <div className="cds-tooltip-source">
            <h4>{messages.recommendationSource}</h4>
            <strong>{provenance.nodeLabel}</strong>
            <span>{provenance.treeName} · {provenance.nodeKey}</span>
          </div>
          <div className="cds-tooltip-references">
            <h4>{messages.guidelineReferences}</h4>
            {provenance.references.length === 0 ? <p>{messages.noGuidelineReference}</p> : (
              <ul>{provenance.references.map((reference) => (
                <li key={`${reference.tree_key}:${reference.node_key}:${reference.reference_order}`}>
                  <strong>{reference.source_title}</strong>
                  {referenceLocator(reference) && <span>{referenceLocator(reference)}</span>}
                  {reference.reference_note && <small>{reference.reference_note}</small>}
                </li>
              ))}</ul>
            )}
          </div>
      </div>
    </div>,
    document.body,
  )

  return (
    <>
      <div className={`cds-order-row ${isAbcdCombination ? 'cds-combination-row' : ''}`}>
        <span className="cds-order-name">{isAbcdCombination ? messages.combinationTherapy : order.name}</span>
        <span className="cds-order-detail">{isAbcdCombination ? combinationDose : order.dose || order.classLabel}</span>
        {order.drugClasses?.length ? (
          <span
            ref={isAbcdCombination ? anchorRef : undefined}
            className={`cds-class-combination ${isAbcdCombination ? 'cds-class-hover-target' : ''}`}
            tabIndex={isAbcdCombination ? 0 : undefined}
            aria-describedby={isAbcdCombination && open ? tooltipId : undefined}
            onMouseEnter={isAbcdCombination ? scheduleOpen : undefined}
            onMouseLeave={isAbcdCombination ? scheduleClose : undefined}
            onFocus={isAbcdCombination ? () => { cancelTimers(); setOpen(true) } : undefined}
            onBlur={isAbcdCombination ? scheduleClose : undefined}
          >
            {order.drugClasses.map((drugClass) => (
              <span className="cds-drug-class-label" key={drugClass.code}>
                {drugClass.label}
              </span>
            ))}
          </span>
        ) : order.classLabel && <span className="cds-order-class">{order.classLabel}</span>}
        <span className="cds-order-source">{messages.sourceNode}: {provenance.nodeLabel}</span>
      </div>
      {tooltip}
    </>
  )
}

function referenceLocator(reference: ExecutedReference): string {
  const sections = Array.isArray(reference.section_path)
    ? reference.section_path.flatMap((item) => (
        typeof item === 'object' && item !== null && !Array.isArray(item) && typeof item.title === 'string'
          ? [item.number ? `${item.title} ${item.number}` : item.title]
          : []
      )).join(' › ')
    : ''
  return [reference.locator, reference.locator_detail, sections].filter(Boolean).join(' · ')
}
