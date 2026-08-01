import { Activity, Building2, CalendarDays, CheckCircle2, ClipboardCheck, HeartPulse, RefreshCw, ShieldCheck, Stethoscope, Target } from 'lucide-react'
import type { ReactNode } from 'react'
import { clinicalFlags, formatBloodPressure, type ShowcasePatient } from './showcasePatients'

export type EvaluationStatus = 'idle' | 'loading' | 'success' | 'error'

function DataField({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return <div className="sc-data-field"><span>{label}</span><strong className={strong ? 'measure' : ''}>{value}</strong></div>
}

function SummaryMetric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="sc-summary-metric"><span className="sc-summary-icon">{icon}</span><span><small>{label}</small><strong>{value}</strong></span></div>
}

function formatTreatmentStage(stage: string): string {
  return stage ? stage.replaceAll('_', ' ').toLowerCase() : 'Lifestyle intervention'
}

export function PatientChart({ patient, status, error, hasRecommendation, onRetry, onViewRecommendation }: {
  patient: ShowcasePatient
  status: EvaluationStatus
  error: string | null
  hasRecommendation: boolean
  onRetry: () => void
  onViewRecommendation: () => void
}) {
  const flags = clinicalFlags(patient.form)
  const careSetting = patient.form.facility_capability === 'FULL_RESOURCES'
    ? 'Full-resource clinic'
    : patient.form.facility_capability === 'LIMITED_RESOURCES' ? 'Limited-resource clinic' : 'Not specified'
  const hasCareSetting = Boolean(patient.form.facility_capability)
  const isMedicationFollowUp = Boolean(patient.form.medication_follow_up_stage)
  const isFollowUp = isMedicationFollowUp || Boolean(patient.form.previous_sbp)
  const pathway = isMedicationFollowUp
    ? 'Medication follow-up'
    : isFollowUp ? 'Lifestyle follow-up' : 'Initial assessment'
  const targetSbp = patient.form.target_sbp_upper || patient.form.previous_target_sbp
  const targetDbp = patient.form.target_dbp_upper || patient.form.previous_target_dbp
  const targetLabel = patient.form.target_sbp_upper ? 'Active target' : 'Previous target'

  return (
    <main className="sc-chart" aria-label={`${patient.name} chart`}>
      <header className="sc-chart-header">
        <div className={`sc-avatar sc-chart-avatar priority-${patient.priority}`}>{patient.initials}</div>
        <div className="sc-chart-identity">
          <span className="sc-eyebrow">Patient chart</span><h1>{patient.name}</h1>
          <p>{patient.form.age}-year-old {patient.sex.toLowerCase()} <span /> {patient.mrn} <span /> {patient.visitType}</p>
        </div>
      </header>
      <div className="sc-chart-layout">
        <div className="sc-chart-content">
          <section className={`sc-vital-band priority-${patient.priority}`} aria-label="Clinical snapshot">
            <div className="sc-primary-vital"><span>Clinic blood pressure</span><strong>{formatBloodPressure(patient.form.current_clinic_sbp, patient.form.current_clinic_dbp)}</strong><small>mmHg · measured today</small></div>
            <div className="sc-summary-metrics">
              <SummaryMetric icon={<ClipboardCheck size={18} />} label="Evaluation pathway" value={pathway} />
              <SummaryMetric icon={<Activity size={18} />} label="CV risk factors" value={`${patient.form.risk_factor_count || '0'} recorded`} />
              <SummaryMetric icon={hasCareSetting ? <Building2 size={18} /> : <HeartPulse size={18} />}
                label={hasCareSetting ? 'Care setting' : 'Visit status'} value={hasCareSetting ? careSetting : patient.status} />
            </div>
          </section>
          <section className="sc-chart-section sc-review-context">
            <header><div><span className="sc-section-icon"><Stethoscope size={17} /></span><div><h2>Visit context</h2><p>Reason for today’s review</p></div></div><span className={`sc-status priority-${patient.priority}`}>{patient.status}</span></header>
            <p className="sc-clinical-note">{patient.note}</p>
          </section>
          <section className="sc-chart-section">
            <header><div><span className="sc-section-icon"><HeartPulse size={17} /></span><div><h2>Decision modifiers</h2><p>Conditions that affect risk or treatment selection</p></div></div></header>
            {flags.length > 0
              ? <div className="sc-flag-list">{flags.map((flag) => <span key={flag}>{flag}</span>)}</div>
              : <div className="sc-clear-state"><ShieldCheck size={18} /><span><strong>No recorded decision modifiers</strong><small>No comorbidities affecting this pathway are recorded.</small></span></div>}
          </section>
          {isFollowUp && (
            <section className="sc-chart-section">
              <header><div><span className="sc-section-icon"><CalendarDays size={17} /></span><div><h2>Follow-up comparison</h2><p>Prior measurement, treatment target, and current stage</p></div></div></header>
              <div className="sc-followup-grid">
                <DataField label="Previous BP" value={formatBloodPressure(patient.form.previous_sbp, patient.form.previous_dbp)} strong />
                <DataField label={targetLabel} value={formatBloodPressure(targetSbp, targetDbp)} strong />
                <DataField label="Treatment stage" value={formatTreatmentStage(patient.form.medication_follow_up_stage)} />
              </div>
            </section>
          )}
        </div>
        <ReviewRail status={status} error={error} hasRecommendation={hasRecommendation} onRetry={onRetry} onViewRecommendation={onViewRecommendation} />
      </div>
    </main>
  )
}

function ReviewRail({ status, error, hasRecommendation, onRetry, onViewRecommendation }: Omit<Parameters<typeof PatientChart>[0], 'patient'>) {
  const state = status === 'success'
    ? { title: 'Recommendation ready', detail: 'The guideline review is complete.', icon: <CheckCircle2 size={21} /> }
    : status === 'error'
      ? { title: 'Review interrupted', detail: 'The clinical service could not complete this review.', icon: <Activity size={21} /> }
      : { title: 'Reviewing this chart', detail: 'Checking BP, risk modifiers, and treatment pathways.', icon: <Activity size={21} /> }

  return (
    <aside className={`sc-review-rail status-${status}`} aria-label="CDSS review status" aria-live="polite">
      <div className="sc-review-heading"><span className="sc-cdss-mark"><Target size={18} /></span><div><strong>Decision support</strong><small>Northstar CDSS</small></div></div>
      <div className="sc-review-state"><span className="sc-review-state-icon">{state.icon}</span><div><strong>{state.title}</strong><p>{state.detail}</p></div></div>
      {status === 'error' && <div className="sc-review-error" role="alert"><strong>Recommendation unavailable</strong><p>{error}</p><button type="button" onClick={onRetry}><RefreshCw size={14} /> Try again</button></div>}
      {status === 'success' && hasRecommendation && <div className="sc-review-actions"><button type="button" onClick={onViewRecommendation}>View recommendation</button><button className="secondary" type="button" onClick={onRetry}><RefreshCw size={13} /> Run again</button></div>}
      <p className="sc-review-disclaimer"><ShieldCheck size={14} /> Decision support does not replace clinical judgment.</p>
    </aside>
  )
}
