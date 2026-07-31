import type { ReactNode } from 'react'

interface ClinicalSectionProps {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
  defaultOpen?: boolean
}

export function ClinicalSection({
  title, subtitle, children, className = '', defaultOpen = true,
}: ClinicalSectionProps) {
  return (
    <details className={`cds-section ${className}`} open={defaultOpen || undefined}>
      <summary className="cds-section-title">
        <span><strong>{title}</strong>{subtitle && <small>{subtitle}</small>}</span>
        <span className="cds-section-chevron" aria-hidden="true">⌄</span>
      </summary>
      <div className="cds-section-content">{children}</div>
    </details>
  )
}
