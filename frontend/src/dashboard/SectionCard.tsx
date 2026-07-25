import type { ReactNode } from 'react'

interface SectionCardProps {
  title: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
  span?: 1 | 2
}

export function SectionCard({ title, subtitle, action, children, span = 1 }: SectionCardProps) {
  return (
    <section className={`dash-card${span === 2 ? ' dash-card-wide' : ''}`}>
      <div className="dash-card-header">
        <div>
          <h3 className="dash-card-title">{title}</h3>
          {subtitle && <p className="dash-card-subtitle">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="dash-card-body">{children}</div>
    </section>
  )
}
