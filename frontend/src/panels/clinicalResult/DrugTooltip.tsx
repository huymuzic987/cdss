import type { CSSProperties } from 'react'
import type { ExecutedReference } from '../../api/types'
import type { RecommendedDrugClass, RecommendedOrder } from '../clinicalDecisionSupportAdapter'
import {
  getClinicalDecisionSupportMessages,
  type ClinicalDecisionSupportLocale,
} from '../clinicalDecisionSupportMessages'
import type { OrderProvenance } from './RecommendedOrderCard'
import { drugClassDisplay, drugSubgroupDisplay, singleDrugGroupDisplay } from './drugClassLabels'

export function DrugTooltip({
  id, order, drugClass, provenance, locale, style, onMouseEnter, onMouseLeave,
}: {
  id: string
  order: RecommendedOrder
  drugClass: RecommendedDrugClass | undefined
  provenance: OrderProvenance
  locale: ClinicalDecisionSupportLocale
  style: CSSProperties
  onMouseEnter: () => void
  onMouseLeave: () => void
}) {
  const messages = getClinicalDecisionSupportMessages(locale)
  const medicines = drugClass?.medicines.length
    ? drugClass.medicines
    : [{ id: order.id, name: order.name, dose: order.dose ?? '', subgroup: order.classLabel }]
  return (
    <div
      id={id}
      className="cds-drug-tooltip"
      role="tooltip"
      style={style}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="cds-tooltip-header">
        <strong>
          {messages.drugGroup}:{' '}
          {drugClass
            ? drugClassDisplay(drugClass.code, drugClass.label, locale)
            : singleDrugGroupDisplay(order.name, order.classLabel, locale)}
        </strong>
        {(drugClass?.doseLabel || order.dose) && (
          <span>{messages.startingDose}: {drugClass?.doseLabel || order.dose}</span>
        )}
      </div>
      <div className="cds-tooltip-medicine-grid">
        {medicines.map((medicine) => (
          <div className="cds-tooltip-medicine" key={medicine.id}>
            <span>
              <strong>{medicine.name}</strong>
              {medicine.subgroup && <small>{drugSubgroupDisplay(medicine.subgroup, locale)}</small>}
            </span>
            <span>{medicine.dose}</span>
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
    </div>
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
