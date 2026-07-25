type Status = 'neutral' | 'success' | 'danger' | 'warning'

interface StatTileProps {
  label: string
  value: string
  hint?: string
  status?: Status
  badge?: string
}

export function StatTile({ label, value, hint, status = 'neutral', badge }: StatTileProps) {
  return (
    <div className={`dash-tile dash-tile-${status}`}>
      <div className="dash-tile-label">{label}</div>
      <div className="dash-tile-value-row">
        <span className="dash-tile-value">{value}</span>
        {badge && <span className={`dash-badge dash-badge-${status}`}>{badge}</span>}
      </div>
      {hint && <div className="dash-tile-hint">{hint}</div>}
    </div>
  )
}
