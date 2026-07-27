import { InfoTooltip } from './InfoTooltip'

type Status = 'neutral' | 'success' | 'danger' | 'warning'

interface StatTileProps {
  label: string
  value: string
  hint?: string
  status?: Status
  badge?: string
  /** Plain-language explanation shown on hover, for parameters that aren't
   * self-evident from their label (e.g. "CDSS-adherence rate"). */
  explain?: string
}

export function StatTile({ label, value, hint, status = 'neutral', badge, explain }: StatTileProps) {
  return (
    <div className={`dash-tile dash-tile-${status}`}>
      <div className="dash-tile-label">
        {label}
        {explain && <InfoTooltip text={explain} />}
      </div>
      <div className="dash-tile-value-row">
        <span className="dash-tile-value">{value}</span>
        {badge && <span className={`dash-badge dash-badge-${status}`}>{badge}</span>}
      </div>
      {hint && <div className="dash-tile-hint">{hint}</div>}
    </div>
  )
}
