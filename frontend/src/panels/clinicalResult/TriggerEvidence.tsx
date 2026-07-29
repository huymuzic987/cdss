interface TriggerEvidenceProps {
  items: { id: string; label: string; value: string }[]
  title: string
  emptyText: string
}

export function TriggerEvidence({ items, title, emptyText }: TriggerEvidenceProps) {
  return (
    <section className="cds-section cds-evidence" aria-labelledby="cds-evidence-title">
      <h2 id="cds-evidence-title">{title}</h2>
      {items.length === 0 ? <p className="cds-empty">{emptyText}</p> : (
        <dl className="cds-evidence-grid">
          {items.map((item) => (
            <div className="cds-evidence-row" key={item.id}><dt>{item.label}</dt><dd>{item.value}</dd></div>
          ))}
        </dl>
      )}
    </section>
  )
}
