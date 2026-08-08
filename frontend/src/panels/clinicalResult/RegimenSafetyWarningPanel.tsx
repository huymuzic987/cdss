import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { RegimenSafetyWarning } from './regimenSafetyWarnings'

interface RegimenSafetyWarningPanelProps {
  locale: ClinicalDecisionSupportLocale
  warnings: RegimenSafetyWarning[]
}

export function RegimenSafetyWarningPanel({ locale, warnings }: RegimenSafetyWarningPanelProps) {
  if (warnings.length === 0) return null
  const vi = locale === 'vi'
  return (
    <div className="cds-regimen-option-warnings cds-regimen-option-warnings--section" role="alert">
      <strong className="cds-regimen-option-warning-heading">{vi ? '⚠ Cần xem xét an toàn trước khi lưu' : '⚠ Safety review before saving'}</strong>
      {warnings.map((warning) => <div className={`cds-regimen-option-warning ${warning.severity === 'ABSOLUTE' ? 'cds-regimen-option-warning--absolute' : 'cds-regimen-option-warning--review'}`} key={`${warning.severity}-${warning.text}`}>{warning.text}</div>)}
    </div>
  )
}
