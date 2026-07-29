import type { DashboardSummaryResponse } from '../../api/types'
import { compact } from '../format'
import { humanize } from '../humanize'
import { DataTable } from '../DataTable'
import { SectionCard } from '../SectionCard'
import { StatTile } from '../StatTile'

export function ImportStatusSection({ status }: { status: DashboardSummaryResponse['fhir_import_status'] }) {
  return (
    <SectionCard title="Data loaded into the system" subtitle="From FHIR R4 bundle imports">
      <div className="dash-efficacy-row">
        <StatTile label="Patients" value={compact(status.total_patients)} />
        <StatTile label="Visits (encounters)" value={compact(status.total_encounters)} />
        <StatTile label="Blood pressure readings" value={compact(status.total_observations)} />
        <StatTile label="Medication records" value={compact(status.total_medication_requests)} />
      </div>
      <DataTable
        columns={[
          { key: 'source', header: 'Source', render: (row) => humanize(row.source_label) },
          { key: 'when', header: 'Imported at', render: (row) => new Date(row.imported_at).toLocaleString() },
          { key: 'patients', header: 'Patients', render: (row) => String(row.patient_count) },
          { key: 'visits', header: 'Visits', render: (row) => String(row.visit_count) },
          { key: 'errors', header: 'Errors', render: (row) => String(row.error_count) },
        ]}
        rows={status.batches}
        emptyLabel="No imports yet."
      />
    </SectionCard>
  )
}
