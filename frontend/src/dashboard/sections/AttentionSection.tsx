import type { DashboardSummaryResponse } from '../../api/types'
import { downloadCsv } from '../csv'
import { humanize } from '../humanize'
import { SectionCard } from '../SectionCard'

interface AttentionSectionProps {
  attention: DashboardSummaryResponse['needs_attention']
  onSelectPatient: (fhirId: string) => void
}

export function AttentionSection({ attention, onSelectPatient }: AttentionSectionProps) {
  return (
    <SectionCard
      title="Patients who need attention"
      subtitle={`${attention.patients.length} patients flagged — uncontrolled blood pressure, overdue, or recently returned early`}
      action={<button
        type="button"
        className="dash-btn dash-btn-small"
        onClick={() => downloadCsv(
          'needs_attention.csv',
          attention.patients.map((patient) => ({ ...patient, reasons: patient.reasons.map(humanize).join('; ') })) as unknown as Record<string, string | number>[],
        )}
      >Export CSV</button>}
      span={2}
    >
      <div className="dash-table-wrap">
        <table className="dash-table">
          <thead><tr><th>Patient</th><th>Why</th><th>Last seen</th><th>Last BP</th><th>Goal</th></tr></thead>
          <tbody>
            {attention.patients.slice(0, 15).map((row) => (
              <tr key={row.patient_fhir_id}>
                <td><button type="button" className="dash-table-row-btn" onClick={() => onSelectPatient(row.patient_fhir_id)}>{row.patient_fhir_id}</button></td>
                <td>{row.reasons.map(humanize).join(', ')}</td>
                <td>{row.last_visit_date}</td>
                <td>{row.clinic_sbp && row.clinic_dbp ? `${row.clinic_sbp}/${row.clinic_dbp} mmHg` : '—'}</td>
                <td>{row.bp_target_sbp && row.bp_target_dbp ? `${row.bp_target_sbp}/${row.bp_target_dbp} mmHg` : '—'}</td>
              </tr>
            ))}
            {attention.patients.length === 0 && <tr><td colSpan={5} className="dash-empty">No patients currently flagged — everyone looks good.</td></tr>}
          </tbody>
        </table>
      </div>
    </SectionCard>
  )
}
