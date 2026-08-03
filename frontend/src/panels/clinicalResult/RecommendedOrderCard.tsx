import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ExecutedReference } from '../../api/types'
import type { RecommendedOrder } from '../clinicalDecisionSupportAdapter'
import {
  getClinicalDecisionSupportMessages,
  type ClinicalDecisionSupportLocale,
} from '../clinicalDecisionSupportMessages'
import { DrugTooltip } from './DrugTooltip'
import { isSingleMedicationOrder } from './orderClassification'

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
  const anchorRef = useRef<HTMLElement | null>(null)
  const openTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [open, setOpen] = useState(false)
  const [activeClassCode, setActiveClassCode] = useState<string | null>(null)
  const [position, setPosition] = useState<{
    top?: number; bottom?: number; left: number; width: number; maxHeight: number
  } | null>(null)
  const tooltipId = `cds-order-${order.id}`.replace(/[^a-zA-Z0-9_-]/g, '-')
  const isAbcdCombination = (order.drugClasses?.length ?? 0) > 1
    && order.drugClasses!.every((item) => /^[ABCD]$/.test(item.code))
  const isCurrentRegimen = order.orderType === 'current-regimen'
  const isSingleMedication = isSingleMedicationOrder(order)
  const combinationDose = order.drugClasses?.[0]?.doseLabel || order.dose
  const selectedDrugClass = isAbcdCombination
    ? order.drugClasses?.find((item) => item.code === activeClassCode)
    : order.drugClasses?.[0]

  function cancelTimers() {
    if (openTimer.current !== null) clearTimeout(openTimer.current)
    if (closeTimer.current !== null) clearTimeout(closeTimer.current)
    openTimer.current = null
    closeTimer.current = null
  }

  function scheduleOpen(code: string | null, anchor: HTMLElement) {
    cancelTimers()
    anchorRef.current = anchor
    setActiveClassCode(code)
    openTimer.current = setTimeout(() => setOpen(true), 90)
  }

  function openImmediately(code: string | null, anchor: HTMLElement) {
    cancelTimers()
    anchorRef.current = anchor
    setActiveClassCode(code)
    setOpen(true)
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
  }, [open, activeClassCode])

  useEffect(() => () => cancelTimers(), [])

  const tooltip = (isAbcdCombination || isSingleMedication) && open && position && createPortal(
    <DrugTooltip
      id={tooltipId}
      order={order}
      drugClass={selectedDrugClass}
      provenance={provenance}
      locale={locale}
      style={position}
      onMouseEnter={cancelTimers}
      onMouseLeave={scheduleClose}
    />,
    document.body,
  )

  return (
    <>
      <div
        className={`cds-order-row ${isAbcdCombination ? 'cds-combination-row' : ''} ${isSingleMedication ? 'cds-single-drug-hover-target' : ''}`}
        tabIndex={isSingleMedication ? 0 : undefined}
        aria-describedby={isSingleMedication && open ? tooltipId : undefined}
        onMouseEnter={isSingleMedication ? (event) => scheduleOpen(null, event.currentTarget) : undefined}
        onMouseLeave={isSingleMedication ? scheduleClose : undefined}
        onFocus={isSingleMedication ? (event) => openImmediately(null, event.currentTarget) : undefined}
        onBlur={isSingleMedication ? scheduleClose : undefined}
      >
        <span className="cds-order-name">{isAbcdCombination && !isCurrentRegimen ? messages.combinationTherapy : order.name}</span>
        <span className="cds-order-detail">
          {isCurrentRegimen ? null : isAbcdCombination ? combinationDose : order.dose || order.classLabel}
        </span>
        {order.drugClasses?.length ? (
          <span className="cds-class-combination">
            {order.drugClasses.map((drugClass) => (
              <span
                className={`cds-drug-class-label ${isAbcdCombination ? 'cds-class-hover-target' : ''}`}
                key={drugClass.code}
                tabIndex={isAbcdCombination ? 0 : undefined}
                aria-describedby={isAbcdCombination && open && activeClassCode === drugClass.code ? tooltipId : undefined}
                onMouseEnter={isAbcdCombination
                  ? (event) => scheduleOpen(drugClass.code, event.currentTarget)
                  : undefined}
                onMouseLeave={isAbcdCombination ? scheduleClose : undefined}
                onFocus={isAbcdCombination
                  ? (event) => openImmediately(drugClass.code, event.currentTarget)
                  : undefined}
                onBlur={isAbcdCombination ? scheduleClose : undefined}
              >
                {/^[ABCD]$/.test(drugClass.code) ? drugClass.code : drugClass.label}
              </span>
            ))}
          </span>
        ) : order.classLabel && <span className="cds-order-class">{order.classLabel}</span>}
      </div>
      {tooltip}
    </>
  )
}
