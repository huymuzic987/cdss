import { ChevronDown } from 'lucide-react'
import type { ReactNode, SyntheticEvent } from 'react'
import './ClinicalSection.css'
import './ClinicalSectionTypography.css'
import './RecommendationModalShared.css'

interface ClinicalSectionProps {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
  defaultOpen?: boolean
  onToggle?: (event: SyntheticEvent<HTMLDetailsElement>) => void
  action?: ReactNode
}

export function ClinicalSection({
  title, subtitle, children, className = '', defaultOpen = true, onToggle, action,
}: ClinicalSectionProps) {
  return (
    <details className={`cds-section ${className}`} open={defaultOpen || undefined} onToggle={onToggle}>
      <summary className="cds-section-title">
        <span><strong>{title}</strong>{subtitle && <small>{subtitle}</small>}</span>
        {action && (
          <span
            className="cds-section-action"
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
            }}
          >
            {action}
          </span>
        )}
        {!defaultOpen && (
          <span className="cds-section-chevron" aria-hidden="true">
            <ChevronDown size={15} strokeWidth={2.25} />
          </span>
        )}
      </summary>
      <div className="cds-section-content">{children}</div>
    </details>
  )
}
