import type { DashboardSummaryResponse } from '../../api/types'
import { BarStat } from '../charts/BarStat'
import { ordinalColor } from '../chartColors'
import { downloadCsv } from '../csv'
import { humanize } from '../humanize'
import { SectionCard } from '../SectionCard'

interface VisitSectionsProps {
  visits: DashboardSummaryResponse['visits']
  onSelectPatient: (fhirId: string) => void
}

export function VisitSections({ visits, onSelectPatient }: VisitSectionsProps) {
  return (
    <>
      <SectionCard
        title="How many follow-ups patients get"
        subtitle="Every bar past 'Visit 1' is a follow-up — shows patients being tracked through return visits"
      >
        <BarStat
          data={visits.visits_by_visit_number.map((item) => ({ label: `Visit ${item.label}`, value: item.count }))}
          colors={visits.visits_by_visit_number.map((_, index) => ordinalColor(index))}
        />
      </SectionCard>
      <SectionCard title="Why patients came back early" subtitle="Reasons recorded for visits that happened ahead of schedule">
        <BarStat
          layout="vertical"
          data={visits.early_revisit_reason_breakdown.map((item) => ({ label: humanize(item.label), value: item.count }))}
        />
      </SectionCard>
      <SectionCard
        title="Overdue for follow-up"
        subtitle={`${visits.overdue_patients.length} patients — scheduled recheck date passed with no new visit`}
        action={<button
          type="button"
          className="dash-btn dash-btn-small"
          onClick={() => downloadCsv('overdue_patients.csv', visits.overdue_patients as unknown as Record<string, string | number>[])}
        >Export CSV</button>}
        span={2}
      >
        {visits.overdue_patients.length === 0 ? <p className="dash-empty">No overdue patients — everyone is up to date.</p> : (
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead><tr><th>Patient</th><th>Last seen</th><th>Should have returned by</th><th>Days overdue</th></tr></thead>
              <tbody>{visits.overdue_patients.slice(0, 10).map((item) => (
                <tr key={item.patient_fhir_id}>
                  <td><button type="button" className="dash-table-row-btn" onClick={() => onSelectPatient(item.patient_fhir_id)}>{item.patient_fhir_id}</button></td>
                  <td>{item.last_visit_date}</td><td>{item.scheduled_next_visit_date}</td><td>{item.days_overdue}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </>
  )
}
