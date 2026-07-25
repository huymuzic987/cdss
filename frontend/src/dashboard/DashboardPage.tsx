import { useEffect, useState } from 'react'
import {
  fetchDashboardCdssUsage,
  fetchDashboardEfficacy,
  fetchDashboardOutcomes,
  fetchDashboardOverview,
  fetchDashboardVisits,
  fetchFhirImportStatus,
  fetchNeedsAttention,
  seedDashboardData,
} from '../api/client'
import type {
  CdssUsageResponse,
  DashboardFilters,
  EfficacyResponse,
  FhirImportStatusResponse,
  NeedsAttentionResponse,
  OutcomesResponse,
  OverviewResponse,
  VisitsResponse,
} from '../api/types'
import { BarStat } from './charts/BarStat'
import { LineStat } from './charts/LineStat'
import { DataTable } from './DataTable'
import { downloadCsv } from './csv'
import { FiltersBar } from './FiltersBar'
import { humanize } from './humanize'
import { SectionCard } from './SectionCard'
import { SeedControls, type SeedSource } from './SeedControls'
import { StatTile } from './StatTile'
import { inverseRateVerdict, rateVerdict } from './verdict'
import './dashboard.css'

const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const compact = (v: number) => new Intl.NumberFormat(undefined, { notation: 'compact' }).format(v)

export function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFilters>({})
  const [refreshKey, setRefreshKey] = useState(0)

  const [overview, setOverview] = useState<OverviewResponse | null>(null)
  const [visits, setVisits] = useState<VisitsResponse | null>(null)
  const [outcomes, setOutcomes] = useState<OutcomesResponse | null>(null)
  const [cdssUsage, setCdssUsage] = useState<CdssUsageResponse | null>(null)
  const [efficacy, setEfficacy] = useState<EfficacyResponse | null>(null)
  const [importStatus, setImportStatus] = useState<FhirImportStatusResponse | null>(null)
  const [needsAttention, setNeedsAttention] = useState<NeedsAttentionResponse | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState<SeedSource | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchDashboardOverview(filters), fetchDashboardVisits(filters), fetchDashboardOutcomes(filters)])
      .then(([o, v, out]) => {
        if (cancelled) return
        setOverview(o)
        setVisits(v)
        setOutcomes(out)
      })
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [filters, refreshKey])

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchDashboardCdssUsage(), fetchDashboardEfficacy(), fetchFhirImportStatus(), fetchNeedsAttention()])
      .then(([u, e, s, n]) => {
        if (cancelled) return
        setCdssUsage(u)
        setEfficacy(e)
        setImportStatus(s)
        setNeedsAttention(n)
      })
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [refreshKey])

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

  const hasData = overview !== null && overview.total_patients > 0

  const onScheduleVerdict = visits ? rateVerdict(visits.on_schedule_rate, 0.8, 0.6) : null
  const adherenceVerdict = efficacy ? rateVerdict(efficacy.overall_adherence_rate, 0.75, 0.5) : null
  const overdueVerdict =
    visits && overview
      ? inverseRateVerdict(overview.total_patients ? visits.overdue_patients.length / overview.total_patients : 0, 0.1, 0.25)
      : null

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
          <h2 className="dash-title">Statistics Dashboard</h2>
          <p className="dash-subtitle">
            A plain-language summary of patients, follow-up visits, and whether following CDSS advice actually helps —
            built from imported FHIR R4 records.
          </p>
        </div>
        <SeedControls seeding={seeding} onSeed={handleSeed} filters={filters} />
      </div>

      <FiltersBar filters={filters} onChange={setFilters} />

      {error && <div className="error-banner">{error}</div>}

      {!hasData && !error && (
        <p className="dash-empty dash-empty-hero">
          No patient data loaded yet. Use "Load preset patients" or "Load 1000 synthetic patients" above to seed the
          dashboard from FHIR R4 bundles.
        </p>
      )}

      {hasData && overview && visits && (
        <div className="dash-kpi-row">
          <StatTile
            label="Total patients"
            value={compact(overview.total_patients)}
            hint="Everyone currently loaded in the system"
          />
          <StatTile
            label="Total visits"
            value={compact(overview.total_visits)}
            hint="Initial diagnosis visits plus every follow-up"
          />
          <StatTile
            label="New patients (30 days)"
            value={compact(overview.new_patients_last_30_days)}
            hint="First visit recorded in the last month"
          />
          <StatTile
            label="Follow-up visits"
            value={compact(visits.follow_up_visit_count)}
            hint="Return visits after the initial diagnosis"
          />
          {onScheduleVerdict && (
            <StatTile
              label="Followed-up on time"
              value={pct(visits.on_schedule_rate)}
              hint="Patients who came back on or after their scheduled recheck date"
              status={onScheduleVerdict.status}
              badge={onScheduleVerdict.badge}
            />
          )}
          <StatTile
            label="Returned early"
            value={pct(visits.early_revisit_rate)}
            hint="Came back before the scheduled date — e.g. side effects, worsening symptoms, wrong medication"
            status="neutral"
          />
          {adherenceVerdict && efficacy && (
            <StatTile
              label="Clinicians followed CDSS advice"
              value={pct(efficacy.overall_adherence_rate)}
              hint="Share of follow-up visits where the actual treatment matched the recommendation"
              status={adherenceVerdict.status}
              badge={adherenceVerdict.badge}
            />
          )}
          {overdueVerdict && (
            <StatTile
              label="Patients overdue for a check-up"
              value={compact(visits.overdue_patients.length)}
              hint="Past their scheduled recheck date with no new visit yet"
              status={overdueVerdict.status}
              badge={overdueVerdict.badge}
            />
          )}
        </div>
      )}

      {hasData && overview && (
        <div className="dash-grid">
          <SectionCard title="Patients by age group" subtitle="How the patient population is spread across age bands">
            <BarStat data={overview.age_distribution.map((c) => ({ label: c.label, value: c.count }))} />
          </SectionCard>

          <SectionCard title="Patients by gender">
            <BarStat data={overview.gender_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))} />
          </SectionCard>

          <SectionCard title="Common existing conditions" subtitle="Share of patients who also have each condition, alongside hypertension">
            <BarStat
              layout="vertical"
              formatValue={(v) => compact(v)}
              data={overview.comorbidity_prevalence.map((r) => ({ label: humanize(r.label), value: r.count }))}
            />
          </SectionCard>

          {visits && (
            <>
              <SectionCard
                title="How many follow-ups patients get"
                subtitle="Every bar past 'Visit 1' is a follow-up — shows patients being tracked through 3 or more return visits"
              >
                <BarStat data={visits.visits_by_visit_number.map((c) => ({ label: `Visit ${c.label}`, value: c.count }))} />
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
                <DataTable
                  columns={[
                    { key: 'id', header: 'Patient', render: (r) => r.patient_fhir_id },
                    { key: 'last', header: 'Last seen', render: (r) => r.last_visit_date },
                    { key: 'sched', header: 'Should have returned by', render: (r) => r.scheduled_next_visit_date },
                    { key: 'overdue', header: 'Days overdue', render: (r) => String(r.days_overdue) },
                  ]}
                  rows={visits.overdue_patients.slice(0, 10)}
                  emptyLabel="No overdue patients — everyone is up to date."
                />
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
                  formatValue={(v) => pct(v)}
                  data={outcomes.outcomes_by_visit_number.map((o) => ({ label: `Visit ${o.visit_number}`, value: o.bp_controlled_rate }))}
                />
              </SectionCard>

              <SectionCard title="Average systolic (top number)" subtitle="mmHg, averaged across all patients at each visit">
                <LineStat
                  data={outcomes.outcomes_by_visit_number
                    .filter((o) => o.avg_sbp !== null)
                    .map((o) => ({ label: `Visit ${o.visit_number}`, value: o.avg_sbp as number }))}
                />
              </SectionCard>

              <SectionCard title="Average diastolic (bottom number)" subtitle="mmHg, averaged across all patients at each visit">
                <LineStat
                  data={outcomes.outcomes_by_visit_number
                    .filter((o) => o.avg_dbp !== null)
                    .map((o) => ({ label: `Visit ${o.visit_number}`, value: o.avg_dbp as number }))}
                />
              </SectionCard>

              <SectionCard title="Blood pressure goals assigned" subtitle="130/80 for higher-risk patients, 140/80 for everyone else">
                <BarStat data={outcomes.bp_target_distribution.map((c) => ({ label: `${c.label} mmHg`, value: c.count }))} />
              </SectionCard>
            </>
          )}

          {cdssUsage && (
            <>
              <SectionCard title="Where patients are treated">
                <BarStat data={cdssUsage.facility_capability_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))} />
              </SectionCard>

              <SectionCard title="Severity at first diagnosis" subtitle="How serious the hypertension was when each patient was first diagnosed">
                <BarStat data={cdssUsage.hypertension_class_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))} />
              </SectionCard>

              <SectionCard title="Overall cardiovascular risk" subtitle="Risk level assigned by the CDSS, combining BP severity with other risk factors">
                <BarStat data={cdssUsage.risk_level_distribution.map((c) => ({ label: humanize(c.label), value: c.count }))} />
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
                  hint="Percentage-point difference in BP control between the two groups above"
                />
                <StatTile
                  label="How often treatment changed between visits"
                  value={pct(efficacy.medication_change_rate)}
                  hint="Share of follow-ups where the medication plan was adjusted from the visit before"
                />
              </div>
              <p className="dash-chart-caption">Share of visits where the clinician followed CDSS advice, by visit number:</p>
              <LineStat
                yDomain={[0, 1]}
                formatValue={(v) => pct(v)}
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

          {needsAttention && (
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
              <DataTable
                columns={[
                  { key: 'id', header: 'Patient', render: (r) => r.patient_fhir_id },
                  { key: 'reasons', header: 'Why', render: (r) => r.reasons.map(humanize).join(', ') },
                  { key: 'last', header: 'Last seen', render: (r) => r.last_visit_date },
                  { key: 'bp', header: 'Last BP', render: (r) => (r.clinic_sbp && r.clinic_dbp ? `${r.clinic_sbp}/${r.clinic_dbp} mmHg` : '—') },
                  { key: 'target', header: 'Goal', render: (r) => (r.bp_target_sbp && r.bp_target_dbp ? `${r.bp_target_sbp}/${r.bp_target_dbp} mmHg` : '—') },
                ]}
                rows={needsAttention.patients.slice(0, 15)}
                emptyLabel="No patients currently flagged — everyone looks good."
              />
            </SectionCard>
          )}
        </div>
      )}
    </div>
  )
}
