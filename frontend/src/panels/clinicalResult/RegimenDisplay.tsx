import { useState, type CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import type { ExecutedReference } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { ClinicalPresentation, FinalRegimenComponent } from '../clinicalPresentation/types'
import { ClinicalSection } from './ClinicalSection'
import { ComponentCatalogDetails } from './RegimenCatalogPopup'
import { recommendedDoseSummary } from './RegimenCatalog'
import { uniqueReferenceDetails } from './RegimenReferenceDetails'
import { RegimenTooltip } from './RegimenTooltip'
import { useRegimenPopupDismissal } from './useRegimenPopupDismissal'
import './RegimenDisplay.css'

export { RegimenPathDisplay } from './RegimenPathDisplay'

interface RegimenDisplayProps {
  presentation: ClinicalPresentation
  references: ExecutedReference[]
  locale: ClinicalDecisionSupportLocale
  includePath?: boolean
}

interface TooltipState {
  optionId: string
  left: number
  top: number
  placement: 'above' | 'below'
}

interface CatalogPopupState extends TooltipState {
  component: FinalRegimenComponent
}

function componentDisplayLabel(
  component: FinalRegimenComponent,
  locale: ClinicalDecisionSupportLocale,
): string {
  void locale
  return component.label
}

export function RegimenDisplay({
  presentation, references, locale, includePath = false,
}: RegimenDisplayProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const [catalogPopup, setCatalogPopup] = useState<CatalogPopupState | null>(null)
  useRegimenPopupDismissal(Boolean(tooltip || catalogPopup), () => {
    setTooltip(null)
    setCatalogPopup(null)
  })
  if (presentation.regimenSteps.length === 0 && presentation.regimenOptions.length === 0) return null
  const vi = locale === 'vi'
  const sourceKeys = new Set(
    presentation.regimenSteps.map((step) => `${step.treeKey}:${step.nodeKey}`),
  )
  const regimenReferences = references.filter(
    (reference) => sourceKeys.has(`${reference.tree_key}:${reference.node_key}`),
  )
  const referenceDetails = uniqueReferenceDetails(regimenReferences)
  const activeOption = presentation.regimenOptions.find(
    (option) => option.id === tooltip?.optionId,
  )

  const showTooltip = (element: HTMLElement, optionId: string) => {
    const rect = element.getBoundingClientRect()
    const tooltipWidth = Math.min(520, window.innerWidth - 32)
    const estimatedHeight = 230
    const placement = rect.bottom + estimatedHeight > window.innerHeight && rect.top > estimatedHeight
      ? 'above'
      : 'below'
    setTooltip({
      optionId,
      left: Math.max(16, Math.min(rect.left, window.innerWidth - tooltipWidth - 16)),
      top: placement === 'above' ? rect.top - 8 : rect.bottom + 8,
      placement,
    })
  }

  return (
    <>
      {includePath && presentation.regimenSteps.length > 0 && (
        <details className="cds-regimen-panel cds-regimen-path" open>
          <summary>{vi ? 'Đường thu thập thuốc' : 'Drug collection path'}</summary>
          <div className="cds-regimen-panel-content">
            {presentation.regimenSteps.map((step) => (
              <div className="cds-regimen-path-step" key={step.id}>
                <span>{step.operation}</span>
                <span><strong>{step.componentLabel || step.instruction}</strong><small>{step.instruction}</small></span>
                <small>{step.doseLabel}</small>
              </div>
            ))}
          </div>
        </details>
      )}
      {presentation.regimenOptions.length > 0 && (
        <ClinicalSection
          className="cds-final-regimens"
          title={vi ? 'Phác đồ thuốc cuối cùng' : 'Final drug regimen'}
          onToggle={(event) => !event.currentTarget.open && setTooltip(null)}
        >
          <div className="cds-regimen-panel-content">
            <div className="cds-regimen-guidance">
              {presentation.regimenOptions.length > 1
                ? (vi ? 'Chọn một trong các phác đồ hoàn chỉnh dưới đây' : 'Choose one complete regimen below')
                : (vi ? 'Dùng tất cả thành phần cùng nhau' : 'Use all components together')}
            </div>
            {presentation.regimenOptions.map((option, optionIndex) => (
              <div
                className="cds-final-regimen"
                key={option.id}
              >
                {presentation.regimenOptions.length > 1 && (
                  <button
                    className="cds-regimen-option-title"
                    type="button"
                    aria-label={`Show details for regimen ${optionIndex + 1}`}
                    aria-expanded={tooltip?.optionId === option.id}
                    style={{ '--option-hue': (optionIndex * 67 + 188) % 360 } as CSSProperties}
                    onClick={(event) => {
                      if (tooltip?.optionId === option.id) {
                        setTooltip(null)
                      } else {
                        showTooltip(event.currentTarget, option.id)
                      }
                    }}
                  >
                    {optionIndex + 1}
                  </button>
                )}
                <div className="cds-regimen-components">
                  {option.components.map((component, componentIndex) => (
                    <div className="cds-regimen-component-group" key={`${component.group}-${component.subgroup ?? ''}-${component.detail}-${component.dose}`}>
                      {componentIndex > 0 && <span className="cds-regimen-and">+</span>}
                      <button
                        className="cds-regimen-component"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          setTooltip(null)
                          const rect = event.currentTarget.getBoundingClientRect()
                          const popupWidth = Math.min(620, window.innerWidth - 32)
                          const estimatedHeight = 360
                          const placement = rect.bottom + estimatedHeight > window.innerHeight && rect.top > estimatedHeight
                            ? 'above'
                            : 'below'
                          setCatalogPopup((current) => (
                            current
                            && current.component.group === component.group
                            && current.component.label === component.label
                            && current.component.subgroup === component.subgroup
                              ? null
                              : {
                                  component,
                                  optionId: option.id,
                                  left: Math.max(16, Math.min(rect.left, window.innerWidth - popupWidth - 16)),
                                  top: placement === 'above' ? rect.top - 8 : rect.bottom + 8,
                                  placement,
                                }
                          ))
                        }}
                      >
                        <strong>{componentDisplayLabel(component, locale)}</strong>
                        <small>{recommendedDoseSummary(component, presentation.regimenCatalog)}</small>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ClinicalSection>
      )}
      {tooltip && activeOption && (
        <RegimenTooltip
          activeOption={activeOption}
          left={tooltip.left}
          locale={locale}
          placement={tooltip.placement}
          referenceDetails={referenceDetails}
          regimenReferences={regimenReferences}
          top={tooltip.top}
        />
      )}
      {catalogPopup && createPortal(
        <ComponentCatalogDetails
          catalog={presentation.regimenCatalog}
          component={catalogPopup.component}
          onClose={() => setCatalogPopup(null)}
          placement={catalogPopup.placement}
          position={{ left: catalogPopup.left, top: catalogPopup.top }}
        />,
        document.body,
      )}
    </>
  )
}
