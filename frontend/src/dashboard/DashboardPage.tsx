import { useEffect, useState } from 'react'
import { fetchDashboardSummary, seedDashboardData } from '../api/client'
import type { DashboardFilters, DashboardSummaryResponse, PatientSearchParams } from '../api/types'
import { downloadCsv } from './csv'
import { FiltersBar } from './FiltersBar'
import { mmHg, pct } from './format'
import { FollowUpKpis, TopKpis } from './DashboardKpis'
import { PatientDetailModal } from './PatientDetailModal'
import { PatientsPanel } from './PatientsPanel'
import { SectionCard } from './SectionCard'
import { SeedControls, type SeedSource } from './SeedControls'
import { AttentionSection } from './sections/AttentionSection'
import { CohortSections } from './sections/CohortSections'
import { EfficacySection } from './sections/EfficacySection'
import { ImportStatusSection } from './sections/ImportStatusSection'
import { OutcomeSections } from './sections/OutcomeSections'
import { UsageSections } from './sections/UsageSections'
import { VisitSections } from './sections/VisitSections'
import './dashboard.css'

export function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFilters>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState<SeedSource | null>(null)
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null)
  const [patientsStatusFilter, setPatientsStatusFilter] = useState<PatientSearchParams['status']>()

  useEffect(() => {
    let cancelled = false
    fetchDashboardSummary(filters)
      .then((response) => !cancelled && setSummary(response))
      .catch((reason: unknown) => !cancelled && setError(reason instanceof Error ? reason.message : String(reason)))
    return () => { cancelled = true }
  }, [filters, refreshKey])

  const handleSeed = async (source: SeedSource) => {
    setSeeding(source)
    setError(null)
    try {
      await seedDashboardData(source)
      setRefreshKey((key) => key + 1)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setSeeding(null)
    }
  }

  const jumpToPatients = (status: PatientSearchParams['status']) => {
    setPatientsStatusFilter(status)
    document.getElementById('dash-patients-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  const { overview, visits, outcomes, cdss_usage: usage, efficacy, fhir_import_status: importStatus, needs_attention: attention } = summary ?? {}
  const hasData = overview !== undefined && overview.total_patients > 0

  const exportCohortCsv = () => {
    if (!overview || !efficacy) return
    const male = overview.gender_distribution.find((item) => item.label === 'male')?.count ?? 0
    const female = overview.gender_distribution.find((item) => item.label === 'female')?.count ?? 0
    downloadCsv('cohort_stats.csv', [{
      total_patients: overview.total_patients,
      male,
      female,
      cdss_adherent_visits: efficacy.adherent_visit_count,
      cdss_adherence_rate: pct(efficacy.overall_adherence_rate),
      mean_sbp: outcomes?.mean_sbp ?? '',
      median_sbp: outcomes?.median_sbp ?? '',
    }])
  }

  return (
    <div className="dashboard">
      <div className="dash-header">
        <div>
          <h2 className="dash-title">Patient Cohort Dashboard</h2>
          <p className="dash-subtitle">Filter the cohort and see the clinical distribution â€” built from imported FHIR R4 records.</p>
        </div>
        <SeedControls seeding={seeding} onSeed={handleSeed} filters={filters} />
      </div>
      <FiltersBar filters={filters} onChange={setFilters} onExportCsv={hasData ? exportCohortCsv : undefined} />
      {error && <div className="error-banner">{error}</div>}
      {!hasData && !error && <p className="dash-empty dash-empty-hero">
        No patient data loaded yet. Use the controls above to seed the dashboard from FHIR R4 bundles.
      </p>}

      {hasData && overview && efficacy && <TopKpis overview={overview} efficacy={efficacy} filters={filters} />}
      {hasData && outcomes && <div className="dash-inline-stats">
        <span>Mean SBP: <strong>{mmHg(outcomes.mean_sbp)}</strong></span>
        <span>Median SBP: <strong>{mmHg(outcomes.median_sbp)}</strong></span>
        <span>Weight: <strong>No data</strong></span>
        <span>BMI: <strong>No data</strong></span>
      </div>}

      <SectionCard title="Find a patient" subtitle="Search, filter by clinical status, then open a patient's visit history." span={2}>
        <div id="dash-patients-section">
          <PatientsPanel onSelect={setSelectedPatient} presetStatus={patientsStatusFilter} />
        </div>
      </SectionCard>

      {hasData && overview && efficacy && <div className="dash-grid">
        <CohortSections overview={overview} outcomes={outcomes} efficacy={efficacy} usage={usage} />
        {visits && <VisitSections visits={visits} onSelectPatient={setSelectedPatient} />}
        {outcomes && <OutcomeSections outcomes={outcomes} />}
        {usage && <UsageSections usage={usage} />}
        <EfficacySection efficacy={efficacy} />
        {importStatus && <ImportStatusSection status={importStatus} />}
        {attention && visits && <AttentionSection attention={attention} onSelectPatient={setSelectedPatient} />}
      </div>}

      {hasData && overview && visits && efficacy && (
        <FollowUpKpis overview={overview} visits={visits} efficacy={efficacy} onJumpToPatients={jumpToPatients} />
      )}
      {selectedPatient && <PatientDetailModal fhirId={selectedPatient} onClose={() => setSelectedPatient(null)} />}
    </div>
  )
}
