import { useEffect, useState } from 'react'
import { fetchDashboardSummary, seedDashboardData } from '../api/client'
import type { DashboardFilters, DashboardSummaryResponse, PatientSearchParams } from '../api/types'
import { BarStat } from './charts/BarStat'
import { LineStat } from './charts/LineStat'
import { DonutStat } from './charts/DonutStat'
import { flatColors, ordinalColor, SECTION_COLORS } from './chartColors'
import { DataTable } from './DataTable'
import { downloadCsv } from './csv'
import { EXPLANATIONS } from './explanations'
import { FiltersBar } from './FiltersBar'
import { humanize } from './humanize'
import { PatientDetailModal } from './PatientDetailModal'
import { PatientsPanel } from './PatientsPanel'
import { SectionCard } from './SectionCard'
import { SeedControls, type SeedSource } from './SeedControls'
import { StatTile } from './StatTile'
import { inverseRateVerdict, rateVerdict } from './verdict'
import './dashboard.css'

const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const compact = (v: number) => new Intl.NumberFormat(undefined, { notation: 'compact' }).format(v)
const mmHg = (v: number | null) => (v === null ? 'No data' : `${v.toFixed(1)} mmHg`)

export function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFilters>({})
  const [refreshKey, setRefreshKey] = useState(0)

  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState<SeedSource | null>(null)

  const [selectedPatient, setSelectedPatient] = useState<string | null>(null)
  const [patientsStatusFilter, setPatientsStatusFilter] = useState<PatientSearchParams['status']>(undefined)

  useEffect(() => {
    let cancelled = false
    fetchDashboardSummary(filters)
      .then((s) => !cancelled && setSummary(s))
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [filters, refreshKey])

  const handleSeed = async (source: SeedSource) => {
    setSeeding(source)
    setError(null)
    try {
      await seedDashboardData(source)
      setRefreshKey((k) => k + 1)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSeeding(null)
    }
  }

  const jumpToPatients = (status: PatientSearchParams['status']) => {
    setPatientsStatusFilter(status)
    document.getElementById('dash-patients-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  const { overview, visits, outcomes, cdss_usage: cdssUsage, efficacy, fhir_import_status: importStatus, needs_attention: needsAttention } =
    summary ?? {}

  const hasData = overview !== undefined && overview.total_patients > 0
  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined)

  const onScheduleVerdict = visits ? rateVerdict(visits.on_schedule_rate, 0.8, 0.6) : null
  const adherenceVerdict = efficacy ? rateVerdict(efficacy.overall_adherence_rate, 0.75, 0.5) : null
  const overdueVerdict =
    visits && overview
      ? inverseRateVerdict(overview.total_patients ? visits.overdue_patients.length / overview.total_patients : 0, 0.1, 0.25)
      : null

  const maleCount = overview?.gender_distribution.find((g) => g.label === 'male')?.count ?? 0
  const femaleCount = overview?.gender_distribution.find((g) => g.label === 'female')?.count ?? 0

  const exportCohortCsv = () => {
    if (!overview || !efficacy) return
    downloadCsv('cohort_stats.csv', [
      {
        total_patients: overview.total_patients,
        male: maleCount,
        female: femaleCount,
        cdss_adherent_visits: efficacy.adherent_visit_count,
        cdss_adherence_rate: pct(efficacy.overall_adherence_rate),
        mean_sbp: outcomes?.mean_sbp ?? '',
        median_sbp: outcomes?.median_sbp ?? '',
      },
    ])
  }

  const effectivenessSentence =
    efficacy &&
    (efficacy.bp_control_rate_when_adherent > 0 || efficacy.bp_control_rate_when_not_adherent > 0) ? (
      <p className="dash-insight">
        When the clinician followed the CDSS recommendation, <strong>{pct(efficacy.bp_control_rate_when_adherent)}</strong>{' '}
        of patients had their blood pressure under control at the next visit — versus only{' '}
        <strong>{pct(efficacy.bp_control_rate_when_not_adherent)}</strong> when the recommendation wasn't followed. That's
        a <strong>{pct(efficacy.effectiveness_delta)}</strong> point advantage for sticking to the CDSS plan.
      </p>
    ) : null

  return (
    <div className="dashboard">
      <div className="dash-header">
        <div>
          <h2 className="dash-title">Patient Cohort Dashboard</h2>
          <p className="dash-subtitle">
            Filter the cohort and see the clinical distribution — built from imported FHIR R4 records.
          </p>
        </div>
        <SeedControls seeding={seeding} onSeed={handleSeed} filters={filters} />
      </div>

      <FiltersBar filters={filters} onChange={setFilters} onExportCsv={hasData ? exportCohortCsv : undefined} />

      {error && <div className="error-banner">{error}</div>}

      {!hasData && !error && (
        <p className="dash-empty dash-empty-hero">
          No patient data loaded yet. Use "Load preset patients" or "Load 1000 synthetic patients" above to seed the
          dashboard from FHIR R4 bundles.
        </p>
      )}

      {hasData && overview && efficacy && (
        <div className="dash-kpi-row">
          <StatTile
            label="Patients (filtered)"
            value={compact(overview.total_patients)}
            hint={hasActiveFilters ? 'Matches the current filters' : 'Everyone currently loaded'}
          />
          <StatTile label="Male" value={compact(maleCount)} />
          <StatTile label="Female" value={compact(femaleCount)} />
          <StatTile
            label="CDSS adherence"
            value={`${efficacy.adherent_visit_count.toLocaleString()} (${pct(efficacy.overall_adherence_rate)})`}
            explain={EXPLANATIONS.adherence}
          />
        </div>
      )}

      {hasData && outcomes && (
        <div className="dash-inline-stats">
          <span>
            Mean SBP: <strong>{mmHg(outcomes.mean_sbp)}</strong>
          </span>
          <span>
            Median SBP: <strong>{mmHg(outcomes.median_sbp)}</strong>
          </span>
          <span>
            Weight: <strong>No data</strong>
          </span>
          <span>
            BMI: <strong>No data</strong>
          </span>
        </div>
      )}

      <SectionCard
        title="Find a patient"
        subtitle="Search by patient ID or department, filter by gender or clinical status, then open a patient to see their full visit history."
        span={2}
      >
        <div id="dash-patients-section">
          <PatientsPanel onSelect={setSelectedPatient} presetStatus={patientsStatusFilter} />
        </div>
      </SectionCard>

      {hasData && overview && (
        <div className="dash-grid">
          <SectionCard
            title="Comorbidities (by ICD-10)"
            subtitle="Share of patients who also have each condition, alongside hypertension — I10 excluded since every patient has it"
          >
            <BarStat
              layout="vertical"
              formatValue={(v) => compact(v)}
              data={overview.comorbidity_prevalence.map((r) => ({ label: humanize(r.label), value: r.count }))}
              colors={flatColors(SECTION_COLORS.comorbidities, overview.comorbidity_prevalence.length)}
            />
            <div className="dash-table-wrap" style={{ marginTop: 10 }}>
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>ICD-10</th>
                    <th>Condition</th>
                    <th>Patients</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.comorbidity_prevalence.map((r) => (
                    <tr key={r.label}>
                      <td>{r.label}</td>
                      <td>{humanize(r.label)}</td>
                      <td>{r.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          {outcomes && (
            <SectionCard
              title="Blood pressure levels (SBP)"
              subtitle="Every visit's systolic reading, bucketed by severity"
            >
              <BarStat
                layout="vertical"
                data={outcomes.sbp_severity_distribution.map((c) => ({ label: c.label, value: c.count }))}
                colors={outcomes.sbp_severity_distribution.map((_, i) => ordinalColor(i))}
              />
            </SectionCard>
          )}

          <SectionCard
            title="Risk factor count"
            subtitle="How many of the tracked risk factors (CAD, heart failure, stroke/TIA, CKD, diabetes, atrial fibrillation, dyslipidemia) each patient has"
          >
            <BarStat
              data={overview.risk_factor_distribution.map((c) => ({ label: c.label, value: c.count }))}
              colors={flatColors(SECTION_COLORS.riskFactorCount, overview.risk_factor_distribution.length)}
            />
          </SectionCard>

          <SectionCard title="Age distribution" subtitle="How the patient population is spread across age bands">
            <BarStat
              data={overview.age_distribution.map((c) => ({ label: c.label, value: c.count }))}
              colors={flatColors(SECTION_COLORS.age, overview.age_distribution.length)}
              showValueLabels
            />
          </SectionCard>

          {efficacy && (
            <SectionCard title="CDSS adherence" subtitle="Share of flagged visits where the clinician followed the CDSS recommendation">
              <DonutStat
                centerLabel={pct(efficacy.overall_adherence_rate)}
                slices={[
                  { label: 'Followed advice', value: efficacy.adherent_visit_count, color: SECTION_COLORS.adherenceYes },
                  { label: "Didn't follow", value: efficacy.non_adherent_visit_count, color: SECTION_COLORS.adherenceNo },
                ]}
              />
            </SectionCard>
          )}

          {cdssUsage && (
            <SectionCard
              title="Antihypertensive drug classes"
              subtitle="Medication records grouped by class across all visits"
              span={2}
            >
              <BarStat
                layout="vertical"
                height={200}
                labelWidth={200}
                data={cdssUsage.drug_class_distribution.map((c) => ({ label: c.label, value: c.count }))}
                colors={flatColors(SECTION_COLORS.drugClasses, cdssUsage.drug_class_distribution.length)}
                showValueLabels
              />
            </SectionCard>
          )}

          <SectionCard title="Patients by gender">
            <BarStat data={overview.gender_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))} />
          </SectionCard>

          {visits && (
            <>
              <SectionCard
                title="How many follow-ups patients get"
                subtitle="Every bar past 'Visit 1' is a follow-up — shows patients being tracked through 3 or more return visits"
              >
                <BarStat
                  data={visits.visits_by_visit_number.map((c) => ({ label: `Visit ${c.label}`, value: c.count }))}
                  colors={visits.visits_by_visit_number.map((_, i) => ordinalColor(i))}
                />
              </SectionCard>

              <SectionCard title="Why patients came back early" subtitle="Reasons recorded for visits that happened ahead of schedule">
                <BarStat
                  layout="vertical"
                  data={visits.early_revisit_reason_breakdown.map((c) => ({ label: humanize(c.label), value: c.count }))}
                />
              </SectionCard>

              <SectionCard
                title="Overdue for follow-up"
                subtitle={`${visits.overdue_patients.length} patients — their scheduled recheck date has already passed with no new visit recorded`}
                action={
                  <button
                    type="button"
                    className="dash-btn dash-btn-small"
                    onClick={() =>
                      downloadCsv('overdue_patients.csv', visits.overdue_patients as unknown as Record<string, string | number>[])
                    }
                  >
                    Export CSV
                  </button>
                }
                span={2}
              >
                {visits.overdue_patients.length === 0 ? (
                  <p className="dash-empty">No overdue patients — everyone is up to date.</p>
                ) : (
                  <div className="dash-table-wrap">
                    <table className="dash-table">
                      <thead>
                        <tr>
                          <th>Patient</th>
                          <th>Last seen</th>
                          <th>Should have returned by</th>
                          <th>Days overdue</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visits.overdue_patients.slice(0, 10).map((o) => (
                          <tr key={o.patient_fhir_id}>
                            <td>
                              <button
                                type="button"
                                className="dash-table-row-btn"
                                onClick={() => setSelectedPatient(o.patient_fhir_id)}
                              >
                                {o.patient_fhir_id}
                              </button>
                            </td>
                            <td>{o.last_visit_date}</td>
                            <td>{o.scheduled_next_visit_date}</td>
                            <td>{o.days_overdue}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </SectionCard>
            </>
          )}

          {outcomes && (
            <>
              <SectionCard
                title="Blood pressure control over time"
                subtitle="Percentage of patients at their BP goal, visit by visit — this should trend upward as treatment works"
              >
                <LineStat
                  yDomain={[0, 1]}
                  formatValue={(v) => pct(v as number)}
                  data={outcomes.outcomes_by_visit_number.map((o) => ({ label: `Visit ${o.visit_number}`, value: o.bp_controlled_rate }))}
                />
              </SectionCard>

              <SectionCard
                title="Average blood pressure"
                subtitle="mmHg, averaged across all patients at each visit — systolic and diastolic shown together, the way BP is actually read"
                span={2}
              >
                <div className="dash-chart-legend">
                  <span className="dash-chart-legend-item">
                    <span className="dash-chart-legend-swatch" style={{ background: 'var(--chart-series-1)' }} />
                    Systolic (top number)
                  </span>
                  <span className="dash-chart-legend-item">
                    <span className="dash-chart-legend-swatch" style={{ background: 'var(--chart-series-2)' }} />
                    Diastolic (bottom number)
                  </span>
                </div>
                <LineStat
                  data={outcomes.outcomes_by_visit_number
                    .filter((o) => o.avg_sbp !== null && o.avg_dbp !== null)
                    .map((o) => ({ label: `Visit ${o.visit_number}`, sbp: o.avg_sbp as number, dbp: o.avg_dbp as number }))}
                  series={[
                    { key: 'sbp', label: 'Systolic' },
                    { key: 'dbp', label: 'Diastolic' },
                  ]}
                />
              </SectionCard>

              <SectionCard
                title="Blood pressure goals assigned"
                subtitle="130/80 for higher-risk patients, 140/80 for everyone else"
              >
                <BarStat
                  data={outcomes.bp_target_distribution.map((c) => ({ label: `${c.label} mmHg`, value: c.count }))}
                  colors={outcomes.bp_target_distribution.map((_, i) => ordinalColor(i))}
                />
              </SectionCard>
            </>
          )}

          {cdssUsage && (
            <>
              <SectionCard title="Where patients are treated">
                <BarStat data={cdssUsage.facility_capability_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))} />
              </SectionCard>

              <SectionCard
                title="Severity at first diagnosis"
                subtitle="How serious the hypertension was when each patient was first diagnosed"
              >
                <BarStat
                  data={cdssUsage.hypertension_class_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))}
                  colors={cdssUsage.hypertension_class_distribution.map((_, i) => ordinalColor(i))}
                />
              </SectionCard>

              <SectionCard
                title="Overall cardiovascular risk"
                subtitle="Risk level assigned by the CDSS, combining BP severity with other risk factors"
              >
                <BarStat
                  data={cdssUsage.risk_level_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))}
                  colors={cdssUsage.risk_level_distribution.map((_, i) => ordinalColor(i))}
                />
              </SectionCard>

              <SectionCard title="Most common CDSS advice" subtitle="The treatment recommendations given most often across all visits">
                <BarStat
                  layout="vertical"
                  height={260}
                  labelWidth={220}
                  data={cdssUsage.recommended_action_frequency.map((c) => ({ label: c.label, value: c.count }))}
                />
              </SectionCard>
            </>
          )}

          {efficacy && (
            <SectionCard
              title="Does following CDSS advice actually help?"
              subtitle="Comparing blood-pressure control at the next visit, based on whether the clinician followed the recommendation"
              span={2}
            >
              {effectivenessSentence}
              <div className="dash-efficacy-row">
                <StatTile
                  label="BP controlled next visit — advice followed"
                  value={pct(efficacy.bp_control_rate_when_adherent)}
                  status="success"
                  badge="Followed advice"
                />
                <StatTile
                  label="BP controlled next visit — advice not followed"
                  value={pct(efficacy.bp_control_rate_when_not_adherent)}
                  status="danger"
                  badge="Didn't follow advice"
                />
                <StatTile
                  label="Advantage from following CDSS advice"
                  value={`+${pct(efficacy.effectiveness_delta)}`}
                  status="success"
                  explain={EXPLANATIONS.effectivenessDelta}
                />
                <StatTile
                  label="How often treatment changed between visits"
                  value={pct(efficacy.medication_change_rate)}
                  explain={EXPLANATIONS.medicationChangeRate}
                />
              </div>
              <p className="dash-chart-caption">Share of visits where the clinician followed CDSS advice, by visit number:</p>
              <LineStat
                yDomain={[0, 1]}
                formatValue={(v) => pct(v as number)}
                data={efficacy.adherence_rate_by_visit_number.map((a) => ({ label: `Visit ${a.visit_number}`, value: a.adherence_rate }))}
              />
            </SectionCard>
          )}

          {importStatus && (
            <SectionCard title="Data loaded into the system" subtitle="From FHIR R4 bundle imports">
              <div className="dash-efficacy-row">
                <StatTile label="Patients" value={compact(importStatus.total_patients)} />
                <StatTile label="Visits (encounters)" value={compact(importStatus.total_encounters)} />
                <StatTile label="Blood pressure readings" value={compact(importStatus.total_observations)} />
                <StatTile label="Medication records" value={compact(importStatus.total_medication_requests)} />
              </div>
              <DataTable
                columns={[
                  { key: 'source', header: 'Source', render: (r) => humanize(r.source_label) },
                  { key: 'when', header: 'Imported at', render: (r) => new Date(r.imported_at).toLocaleString() },
                  { key: 'patients', header: 'Patients', render: (r) => String(r.patient_count) },
                  { key: 'visits', header: 'Visits', render: (r) => String(r.visit_count) },
                  { key: 'errors', header: 'Errors', render: (r) => String(r.error_count) },
                ]}
                rows={importStatus.batches}
                emptyLabel="No imports yet."
              />
            </SectionCard>
          )}

          {needsAttention && overdueVerdict && onScheduleVerdict && adherenceVerdict && visits && (
            <SectionCard
              title="Patients who need attention"
              subtitle={`${needsAttention.patients.length} patients flagged — uncontrolled blood pressure, overdue for a check-up, or recently returned early`}
              action={
                <button
                  type="button"
                  className="dash-btn dash-btn-small"
                  onClick={() =>
                    downloadCsv(
                      'needs_attention.csv',
                      needsAttention.patients.map((p) => ({ ...p, reasons: p.reasons.map(humanize).join('; ') })) as unknown as Record<
                        string,
                        string | number
                      >[],
                    )
                  }
                >
                  Export CSV
                </button>
              }
              span={2}
            >
              <div className="dash-table-wrap">
                <table className="dash-table">
                  <thead>
                    <tr>
                      <th>Patient</th>
                      <th>Why</th>
                      <th>Last seen</th>
                      <th>Last BP</th>
                      <th>Goal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {needsAttention.patients.slice(0, 15).map((r) => (
                      <tr key={r.patient_fhir_id}>
                        <td>
                          <button
                            type="button"
                            className="dash-table-row-btn"
                            onClick={() => setSelectedPatient(r.patient_fhir_id)}
                          >
                            {r.patient_fhir_id}
                          </button>
                        </td>
                        <td>{r.reasons.map(humanize).join(', ')}</td>
                        <td>{r.last_visit_date}</td>
                        <td>{r.clinic_sbp && r.clinic_dbp ? `${r.clinic_sbp}/${r.clinic_dbp} mmHg` : '—'}</td>
                        <td>{r.bp_target_sbp && r.bp_target_dbp ? `${r.bp_target_sbp}/${r.bp_target_dbp} mmHg` : '—'}</td>
                      </tr>
                    ))}
                    {needsAttention.patients.length === 0 && (
                      <tr>
                        <td colSpan={5} className="dash-empty">No patients currently flagged — everyone looks good.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </SectionCard>
          )}
        </div>
      )}

      {hasData && overview && (
        <div className="dash-kpi-row" style={{ marginTop: 4 }}>
          {onScheduleVerdict && visits && (
            <StatTile
              label="Followed-up on time"
              value={pct(visits.on_schedule_rate)}
              status={onScheduleVerdict.status}
              badge={onScheduleVerdict.badge}
              explain={EXPLANATIONS.onSchedule}
            />
          )}
          {visits && (
            <StatTile
              label="Returned early"
              value={pct(visits.early_revisit_rate)}
              status="neutral"
              explain={EXPLANATIONS.earlyReturn}
            />
          )}
          {overdueVerdict && visits && (
            <button
              type="button"
              className="dash-tile-link"
              onClick={() => jumpToPatients('overdue')}
              title="View overdue patients"
            >
              <StatTile
                label="Patients overdue for a check-up"
                value={compact(visits.overdue_patients.length)}
                status={overdueVerdict.status}
                badge={overdueVerdict.badge}
                explain={EXPLANATIONS.overdue}
              />
            </button>
          )}
          <StatTile
            label="New patients (30 days)"
            value={compact(overview.new_patients_last_30_days)}
            hint="First visit recorded in the last month"
          />
        </div>
      )}

      {selectedPatient && (
        <PatientDetailModal fhirId={selectedPatient} onClose={() => setSelectedPatient(null)} />
      )}
    </div>
  )
}
