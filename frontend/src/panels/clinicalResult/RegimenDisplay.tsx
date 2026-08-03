import { useState, type CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import type { ExecutedReference, JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { ClinicalPresentation, FinalRegimenComponent, RegimenMedicine } from '../clinicalPresentation/types'
import './RegimenDisplay.css'

interface RegimenDisplayProps {
  presentation: ClinicalPresentation
  references: ExecutedReference[]
  locale: ClinicalDecisionSupportLocale
  includePath?: boolean
}

export function RegimenPathDisplay({
  presentation, locale,
}: Pick<RegimenDisplayProps, 'presentation' | 'locale'>) {
  if (presentation.regimenSteps.length === 0) return null
  const vi = locale === 'vi'
  return (
    <details className="cds-regimen-panel cds-regimen-path cds-regimen-path-in-decision" open>
      <summary>{vi ? 'Đường thu thập thuốc' : 'Drug collection path'}</summary>
      <div className="cds-regimen-panel-content">
        {presentation.regimenSteps.map((step) => (
          <div className="cds-regimen-path-step" key={step.id}>
            <span>{step.operation}</span>
            <span>
              <strong>{step.componentLabel || step.instruction}</strong>
              <small>{step.instruction}</small>
            </span>
            <small>{step.doseLabel}</small>
          </div>
        ))}
      </div>
    </details>
  )
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

const GROUP_NAMES = {
  A: 'RAS: ACE inhibitor / ARB / ARNI',
  B: 'Beta-blocker',
  C: 'Calcium-channel blocker',
  D: 'Diuretic',
  MRA: 'Mineralocorticoid receptor antagonist',
  SGLT2i: 'SGLT2 inhibitor',
  GLP1RA: 'GLP-1 receptor agonist',
  Others: 'Other medicine',
} as const

export function RegimenDisplay({
  presentation, references, locale, includePath = false,
}: RegimenDisplayProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const [catalogPopup, setCatalogPopup] = useState<CatalogPopupState | null>(null)
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
        <details
          className="cds-regimen-panel cds-final-regimens"
          open
          onToggle={(event) => !event.currentTarget.open && setTooltip(null)}
        >
          <summary>{vi ? 'Phác đồ thuốc cuối cùng' : 'Final drug regimen'}</summary>
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
                    <div className="cds-regimen-component-group" key={`${component.group}-${component.detail}-${component.dose}`}>
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
                        <strong>{component.label}</strong>
                        <small>{recommendedDoseSummary(component, presentation.regimenCatalog)}</small>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
      {tooltip && activeOption && createPortal(
        <div
          className={`cds-regimen-row-tooltip cds-regimen-tooltip-${tooltip.placement}`}
          id={`${activeOption.id}-details`}
          role="tooltip"
          style={{ left: tooltip.left, top: tooltip.top }}
        >
          <strong>{vi ? 'Chi tiết phác đồ' : 'Regimen details'}</strong>
          <div className="cds-regimen-group-details">
            {activeOption.components.map((component) => (
              <span key={`${component.group}:${component.label}`}>
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
      )}
      {catalogPopup && createPortal(
        <ComponentCatalogDetails
          component={catalogPopup.component}
          catalog={presentation.regimenCatalog}
          placement={catalogPopup.placement}
          position={{ left: catalogPopup.left, top: catalogPopup.top }}
          onClose={() => setCatalogPopup(null)}
        />,
        document.body,
      )}
    </>
  )
}

function ComponentCatalogDetails({
  component, catalog, placement, position, onClose,
}: {
  component: FinalRegimenComponent
  catalog: Record<string, RegimenMedicine[]>
  placement: 'above' | 'below'
  position: { left: number, top: number }
  onClose: () => void
}) {
  const isSpecificMedicine = isSpecific(component)
  const medicines = componentMedicines(component, catalog)
  const subgroups = Array.from(new Set(medicines.map((medicine) => medicine.subgroup).filter(Boolean)))
  return (
    <div
      className={`cds-regimen-catalog-details cds-regimen-catalog-${placement}`}
      role="dialog"
      aria-label={`${component.label} drug details`}
      style={position}
    >
      <div className="cds-regimen-catalog-heading">
        <span>
          <strong>{component.label}{isSpecificMedicine ? '' : `: ${GROUP_NAMES[component.group]}`}</strong>
          {!isSpecificMedicine && subgroups.length > 0 && <small>Includes: {subgroups.join(' / ')}</small>}
        </span>
        <button type="button" onClick={onClose} aria-label="Close drug details">×</button>
      </div>
      {isSpecificMedicine && <span>Drug group: <b>{component.group}</b> · {GROUP_NAMES[component.group]}</span>}
      {medicines.length === 0 ? (
        <small>No catalogued medicines are available for this group.</small>
      ) : medicines.map((medicine) => (
        <div className="cds-regimen-medicine-detail" key={medicine.id || medicine.name}>
          <div className="cds-regimen-medicine-heading">
            {!isSpecificMedicine && <strong>{medicine.name}</strong>}
            <span>{medicine.route || 'Route not recorded'} / SNOMED CT: {medicine.snomedCode || 'Not recorded'}</span>
          </div>
          <div className="cds-regimen-dose-comparison">
            <span className={activeDose(component.dose) === 'low' ? 'cds-active-dose' : ''}>
              Low: {medicine.doseLow || '-'}
            </span>
            <span className={activeDose(component.dose) === 'usual' ? 'cds-active-dose' : ''}>
              Usual: {medicine.doseUsual || '-'}
            </span>
            <span className={activeDose(component.dose) === 'max' ? 'cds-active-dose' : ''}>
              Maximum: {medicine.doseMax || '-'}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

function activeDose(strategy: string): 'low' | 'usual' | 'max' {
  const normalized = strategy.toLocaleLowerCase()
  if (normalized.includes('maximum') || normalized.includes('tối đa')) return 'max'
  if (normalized.includes('usual') || normalized.includes('thông thường')) return 'usual'
  return 'low'
}

function componentMedicines(
  component: FinalRegimenComponent,
  catalog: Record<string, RegimenMedicine[]>,
): RegimenMedicine[] {
  const allMedicines = catalog.__all__ ?? Array.from(
    new Map(Object.values(catalog).flat().map((medicine) => [medicine.id || medicine.name, medicine])).values(),
  )
  if (!isSpecific(component)) {
    const grouped = catalog[component.group]
    if (grouped && grouped.length > 0) return grouped
    return allMedicines.filter((medicine) => medicineInGroup(medicine, component.group))
  }
  const label = component.label.toLocaleLowerCase()
  return allMedicines.filter((medicine) => {
    const name = medicine.name.toLocaleLowerCase()
    return name === label || label.includes(name)
  })
}

function medicineInGroup(medicine: RegimenMedicine, group: FinalRegimenComponent['group']): boolean {
  if (group === 'MRA') return medicine.subgroup.toLocaleUpperCase().includes('MRA')
  if (group === 'Others') {
    return !['A', 'B', 'C', 'D', 'SGLT2i'].includes(medicine.group)
  }
  return medicine.group.toLocaleLowerCase() === group.toLocaleLowerCase()
}

function isSpecific(component: FinalRegimenComponent): boolean {
  return component.label.toLocaleLowerCase() !== component.group.toLocaleLowerCase()
}

function recommendedDoseSummary(
  component: FinalRegimenComponent,
  catalog: Record<string, RegimenMedicine[]>,
): string {
  if (!isSpecific(component)) return component.dose
  const doseKey = activeDose(component.dose)
  const doses = Array.from(new Set(componentMedicines(component, catalog).map((medicine) => (
    doseKey === 'max' ? medicine.doseMax : doseKey === 'usual' ? medicine.doseUsual : medicine.doseLow
  )).filter(Boolean)))
  return doses.length > 0 ? doses.join(' / ') : component.dose
}

function uniqueReferenceDetails(references: ExecutedReference[]): string[] {
  return Array.from(new Set(references.flatMap((reference) => {
    const section = sectionLabel(reference.section_path)
    const locator = reference.locator?.trim()
    return [section, locator].filter((value): value is string => Boolean(value))
  })))
}

function sectionLabel(value: JsonValue): string {
  if (!Array.isArray(value)) return ''
  return value.flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return []
    const number = typeof item.number === 'string' ? item.number.trim() : ''
    const title = typeof item.title === 'string' ? item.title.trim() : ''
    if (!number && !title) return []
    return [`Mục ${number}${number && title ? '. ' : ''}${title}`]
  }).join(' · ')
}
