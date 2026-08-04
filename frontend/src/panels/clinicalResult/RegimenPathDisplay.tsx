import type { ClinicalPresentation } from '../clinicalPresentation/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

export function RegimenPathDisplay({
  presentation, locale,
}: {
  presentation: ClinicalPresentation
  locale: ClinicalDecisionSupportLocale
}) {
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
