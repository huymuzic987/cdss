import { createPortal } from 'react-dom'
import type { ExecutedReference } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, FinalRegimenOption } from '../clinicalPresentation/types'
import { GROUP_NAMES } from './RegimenCatalog'

interface RegimenTooltipProps {
  activeOption: FinalRegimenOption
  placement: 'above' | 'below'
  left: number
  top: number
  locale: ClinicalDecisionSupportLocale
  regimenReferences: ExecutedReference[]
  referenceDetails: string[]
}

export function RegimenTooltip({
  activeOption,
  placement,
  left,
  top,
  locale,
  regimenReferences,
  referenceDetails,
}: RegimenTooltipProps) {
  const vi = locale === 'vi'
  return createPortal(
    <div
      className={`cds-regimen-row-tooltip cds-regimen-tooltip-${placement}`}
      id={`${activeOption.id}-details`}
      role="tooltip"
      style={{ left, top }}
    >
      <strong>{vi ? 'Chi tiết phác đồ' : 'Regimen details'}</strong>
      <div className="cds-regimen-group-details">
        {activeOption.components.map((component: FinalRegimenComponent) => (
          <span key={`${component.group}:${component.subgroup ?? ''}:${component.label}`}>
            <b>{component.label}</b>: {GROUP_NAMES[component.group]}
          </span>
        ))}
      </div>
      {regimenReferences.length > 0 && (
        <div className="cds-regimen-reference-details">
          <strong>{regimenReferences[0]?.source_title}</strong>
          {referenceDetails.map((detail) => <span key={detail}>{detail}</span>)}
        </div>
      )}
    </div>,
    document.body,
  )
}
