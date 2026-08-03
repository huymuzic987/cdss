import { Fragment } from 'react'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { ClinicalPresentation } from '../clinicalPresentation/types'
import './RegimenDisplay.css'

interface RegimenDisplayProps {
  presentation: ClinicalPresentation
  locale: ClinicalDecisionSupportLocale
}

export function RegimenDisplay({ presentation, locale }: RegimenDisplayProps) {
  if (presentation.regimenSteps.length === 0 && presentation.regimenOptions.length === 0) return null
  const vi = locale === 'vi'
  return (
    <>
      {presentation.regimenSteps.length > 0 && (
        <div className="cds-regimen-path">
          <strong>{vi ? 'Đường thu thập thuốc' : 'Drug collection path'}</strong>
          {presentation.regimenSteps.map((step) => (
            <div className="cds-regimen-path-step" key={step.id}>
              <span>{step.operation}</span>
              <span><strong>{step.componentLabel || step.instruction}</strong><small>{step.instruction}</small></span>
              <small>{step.doseLabel}</small>
            </div>
          ))}
        </div>
      )}
      {presentation.regimenOptions.length > 0 && (
        <div className="cds-final-regimens">
          <strong>{vi ? 'Phác đồ thuốc cuối cùng' : 'Final drug regimen'}</strong>
          <div className="cds-regimen-guidance">
            {presentation.regimenOptions.length > 1
              ? (vi ? 'Chọn một phác đồ hoàn chỉnh' : 'Choose one complete regimen')
              : (vi ? 'Dùng tất cả thành phần cùng nhau' : 'Use all components together')}
          </div>
          {presentation.regimenOptions.map((option, optionIndex) => (
            <Fragment key={option.id}>
              {optionIndex > 0 && <div className="cds-regimen-or">{vi ? 'HOẶC' : 'OR'}</div>}
              <div className="cds-final-regimen">
                <strong className="cds-regimen-option-title">{vi ? 'Phương án' : 'Option'} {optionIndex + 1}</strong>
                <div className="cds-regimen-components">
                  {option.components.map((component, componentIndex) => (
                    <div className="cds-regimen-component-group" key={`${component.group}-${component.detail}-${component.dose}`}>
                      {componentIndex > 0 && <span className="cds-regimen-and">+</span>}
                      <span className="cds-regimen-component">
                        <strong>{component.label}</strong>
                        <small>{component.detail}</small>
                        <small>{component.dose}</small>
                      </span>
                    </div>
                  ))}
                </div>
                <small className="cds-regimen-together">{vi ? 'Dùng tất cả thành phần cùng nhau' : 'Use all components together'}</small>
              </div>
            </Fragment>
          ))}
        </div>
      )}
    </>
  )
}
