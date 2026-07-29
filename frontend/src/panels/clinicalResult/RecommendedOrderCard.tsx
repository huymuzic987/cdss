import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { RecommendedDrugClass, RecommendedOrder } from '../clinicalDecisionSupportAdapter'
import { getClinicalDecisionSupportMessages, type ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

function DrugClassDetails({ drugClass, orderId, locale }: {
  drugClass: RecommendedDrugClass
  orderId: string
  locale: ClinicalDecisionSupportLocale
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const anchorRef = useRef<HTMLDivElement>(null)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState<{
    top?: number; bottom?: number; left: number; width: number; maxHeight: number
  } | null>(null)
  const tooltipId = `cds-class-${orderId}-${drugClass.code}`.replace(/[^a-zA-Z0-9_-]/g, '-')

  function cancelClose() {
    if (closeTimerRef.current !== null) {
      clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
  }
  function scheduleClose() {
    cancelClose()
    closeTimerRef.current = setTimeout(() => setOpen(false), 180)
  }

  useLayoutEffect(() => {
    if (!open) return
    function updatePosition() {
      const anchor = anchorRef.current
      if (!anchor) return
      const rect = anchor.getBoundingClientRect()
      const margin = 12
      const gap = 8
      const width = Math.min(720, window.innerWidth - margin * 2)
      const left = Math.min(Math.max(margin, rect.left), Math.max(margin, window.innerWidth - width - margin))
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

  useEffect(() => () => cancelClose(), [])

  const popover = open && position && createPortal(
    <div
      className="cds-drug-tooltip"
      id={tooltipId}
      role="tooltip"
      style={position}
      onMouseEnter={cancelClose}
      onMouseLeave={scheduleClose}
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
    </div>,
    document.body,
  )

  return (
    <>
      <div
        ref={anchorRef}
        className="cds-drug-class"
        tabIndex={0}
        aria-describedby={open ? tooltipId : undefined}
        onMouseEnter={() => { cancelClose(); setOpen(true) }}
        onMouseLeave={scheduleClose}
        onFocus={() => { cancelClose(); setOpen(true) }}
        onBlur={scheduleClose}
      >
        <span className="cds-drug-class-label">{drugClass.label}</span>
      </div>
      {popover}
    </>
  )
}

export function RecommendedOrderCard({ order, locale }: {
  order: RecommendedOrder
  locale: ClinicalDecisionSupportLocale
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
