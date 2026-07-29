import type { DashboardSummaryResponse } from '../../api/types'
import { LineStat } from '../charts/LineStat'
import { EXPLANATIONS } from '../explanations'
import { pct } from '../format'
import { SectionCard } from '../SectionCard'
import { StatTile } from '../StatTile'

export function EfficacySection({ efficacy }: { efficacy: DashboardSummaryResponse['efficacy'] }) {
  const hasComparison = efficacy.bp_control_rate_when_adherent > 0
    || efficacy.bp_control_rate_when_not_adherent > 0
  return (
    <SectionCard
      title="Does following CDSS advice actually help?"
      subtitle="Comparing blood-pressure control at the next visit, based on whether the clinician followed the recommendation"
      span={2}
    >
      {hasComparison && <p className="dash-insight">
        When the clinician followed the CDSS recommendation, <strong>{pct(efficacy.bp_control_rate_when_adherent)}</strong>{' '}
        of patients had controlled blood pressure at the next visit — versus{' '}
        <strong>{pct(efficacy.bp_control_rate_when_not_adherent)}</strong> when it wasn't followed. That's a{' '}
        <strong>{pct(efficacy.effectiveness_delta)}</strong> point advantage.
      </p>}
      <div className="dash-efficacy-row">
        <StatTile label="BP controlled next visit — advice followed" value={pct(efficacy.bp_control_rate_when_adherent)} status="success" badge="Followed advice" />
        <StatTile label="BP controlled next visit — advice not followed" value={pct(efficacy.bp_control_rate_when_not_adherent)} status="danger" badge="Didn't follow advice" />
        <StatTile label="Advantage from following CDSS advice" value={`+${pct(efficacy.effectiveness_delta)}`} status="success" explain={EXPLANATIONS.effectivenessDelta} />
        <StatTile label="How often treatment changed between visits" value={pct(efficacy.medication_change_rate)} explain={EXPLANATIONS.medicationChangeRate} />
      </div>
      <p className="dash-chart-caption">Share of visits where the clinician followed CDSS advice, by visit number:</p>
      <LineStat
        yDomain={[0, 1]}
        formatValue={(value) => pct(value as number)}
        data={efficacy.adherence_rate_by_visit_number.map((item) => ({ label: `Visit ${item.visit_number}`, value: item.adherence_rate }))}
      />
    </SectionCard>
  )
}
