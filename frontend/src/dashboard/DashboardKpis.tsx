import type { DashboardFilters, DashboardSummaryResponse, PatientSearchParams } from '../api/types'
import { EXPLANATIONS } from './explanations'
import { compact, pct } from './format'
import { StatTile } from './StatTile'
import { inverseRateVerdict, rateVerdict } from './verdict'

interface TopKpisProps {
  overview: DashboardSummaryResponse['overview']
  efficacy: DashboardSummaryResponse['efficacy']
  filters: DashboardFilters
}

export function TopKpis({ overview, efficacy, filters }: TopKpisProps) {
  const male = overview.gender_distribution.find((item) => item.label === 'male')?.count ?? 0
  const female = overview.gender_distribution.find((item) => item.label === 'female')?.count ?? 0
  const hasFilters = Object.values(filters).some((value) => value !== undefined)
  return (
    <div className="dash-kpi-row">
      <StatTile label="Patients (filtered)" value={compact(overview.total_patients)} hint={hasFilters ? 'Matches the current filters' : 'Everyone currently loaded'} />
      <StatTile label="Male" value={compact(male)} />
      <StatTile label="Female" value={compact(female)} />
      <StatTile label="CDSS adherence" value={`${efficacy.adherent_visit_count.toLocaleString()} (${pct(efficacy.overall_adherence_rate)})`} explain={EXPLANATIONS.adherence} />
    </div>
  )
}

interface FollowUpKpisProps {
  overview: DashboardSummaryResponse['overview']
  visits: DashboardSummaryResponse['visits']
  efficacy: DashboardSummaryResponse['efficacy']
  onJumpToPatients: (status: PatientSearchParams['status']) => void
}

export function FollowUpKpis({ overview, visits, efficacy, onJumpToPatients }: FollowUpKpisProps) {
  const onSchedule = rateVerdict(visits.on_schedule_rate, 0.8, 0.6)
  const overdue = inverseRateVerdict(
    overview.total_patients ? visits.overdue_patients.length / overview.total_patients : 0,
    0.1,
    0.25,
  )
  rateVerdict(efficacy.overall_adherence_rate, 0.75, 0.5)
  return (
    <div className="dash-kpi-row" style={{ marginTop: 4 }}>
      <StatTile label="Followed-up on time" value={pct(visits.on_schedule_rate)} status={onSchedule.status} badge={onSchedule.badge} explain={EXPLANATIONS.onSchedule} />
      <StatTile label="Returned early" value={pct(visits.early_revisit_rate)} status="neutral" explain={EXPLANATIONS.earlyReturn} />
      <button type="button" className="dash-tile-link" onClick={() => onJumpToPatients('overdue')} title="View overdue patients">
        <StatTile label="Patients overdue for a check-up" value={compact(visits.overdue_patients.length)} status={overdue.status} badge={overdue.badge} explain={EXPLANATIONS.overdue} />
      </button>
      <StatTile label="New patients (30 days)" value={compact(overview.new_patients_last_30_days)} hint="First visit recorded in the last month" />
    </div>
  )
}
