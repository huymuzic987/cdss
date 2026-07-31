import type { ImportantPathStep } from './criticalSummaryTypes'

interface ImportantDecisionPathProps {
  steps: ImportantPathStep[]
  emptyText: string
}

export function ImportantDecisionPath({ steps, emptyText }: ImportantDecisionPathProps) {
  if (steps.length === 0) return <p className="cds-empty">{emptyText}</p>
  return (
    <ol className="cds-path-list">
      {steps.map((step, index) => (
        <li className={`cds-path-row cds-path-${step.kind}`} key={step.id}>
          <span className="cds-path-index">{index + 1}</span>
          <span className="cds-path-content">
            <strong>{step.label}</strong>
            {step.detail && <span>{step.detail}</span>}
          </span>
          <small>{step.treeName}</small>
        </li>
      ))}
    </ol>
  )
}
