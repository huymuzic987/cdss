import { useEffect, useState } from 'react'
import { fetchPatientDetail } from '../api/client'
import type { PatientDetailResponse } from '../api/types'
import { humanize } from './humanize'
import { LineStat } from './charts/LineStat'

interface PatientDetailModalProps {
  fhirId: string
  onClose: () => void
}

export function PatientDetailModal({ fhirId, onClose }: PatientDetailModalProps) {
  const [patient, setPatient] = useState<PatientDetailResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setPatient(null)
    setError(null)
    fetchPatientDetail(fhirId)
      .then((p) => !cancelled && setPatient(p))
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [fhirId])

  const bpTrend =
    patient?.visits
      .filter((v) => v.clinic_sbp !== null && v.clinic_dbp !== null)
      .map((v) => ({ label: `Visit ${v.visit_number}`, sbp: v.clinic_sbp as number, dbp: v.clinic_dbp as number })) ?? []

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-header-title">{fhirId}</div>
            {patient && (
              <div className="modal-header-sub">
                {patient.department ?? 'No department recorded'}
                {patient.gender ? ` · ${humanize(patient.gender)}` : ''}
                {patient.birth_date ? ` · Born ${patient.birth_date}` : ''}
              </div>
            )}
          </div>
          <button type="button" className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {error && <div className="error-banner">{error}</div>}
          {!patient && !error && <p className="dash-empty">Loading patient…</p>}

          {patient && (
            <>
              <div className="dash-patient-header">
                <span><strong>{patient.visits.length}</strong> visits recorded</span>
                <span><strong>{patient.risk_factor_count}</strong> risk factors</span>
              </div>

              {patient.conditions.length > 0 && (
                <div className="dash-patient-chips">
                  {patient.conditions
                    .filter((c) => c.icd10_code !== 'I10')
                    .map((c, i) => (
                      <span key={i} className="dash-chip">
                        {c.icd10_code ? humanize(c.icd10_code) : c.condition_text ?? 'Condition'}
                      </span>
                    ))}
                </div>
              )}

              {bpTrend.length > 1 && (
                <>
                  <p className="dash-chart-caption">Blood pressure across visits (mmHg):</p>
                  <div className="dash-chart-legend">
                    <span className="dash-chart-legend-item">
                      <span className="dash-chart-legend-swatch" style={{ background: 'var(--chart-series-1)' }} />
                      Systolic
                    </span>
                    <span className="dash-chart-legend-item">
                      <span className="dash-chart-legend-swatch" style={{ background: 'var(--chart-series-2)' }} />
                      Diastolic
                    </span>
                  </div>
                  <LineStat
                    data={bpTrend}
                    series={[
                      { key: 'sbp', label: 'Systolic' },
                      { key: 'dbp', label: 'Diastolic' },
                    ]}
                  />
                </>
              )}

              <p className="dash-chart-caption">Visit history:</p>
              {[...patient.visits].reverse().map((v) => (
                <div key={v.visit_number} className="dash-visit-card">
                  <div className="dash-visit-card-header">
                    <span className="dash-visit-card-title">Visit {v.visit_number} — {v.visit_date}</span>
                    {v.is_early_revisit && <span className="dash-badge dash-badge-warning">Early revisit</span>}
                  </div>
                  <div className="dash-visit-card-body">
                    <span>
                      BP: <strong>{v.clinic_sbp && v.clinic_dbp ? `${v.clinic_sbp}/${v.clinic_dbp} mmHg` : '—'}</strong>
                    </span>
                    <span>
                      Target: <strong>{v.bp_target_sbp && v.bp_target_dbp ? `${v.bp_target_sbp}/${v.bp_target_dbp} mmHg` : '—'}</strong>
                    </span>
                    <span>
                      Controlled: <strong>{v.bp_controlled === null ? '—' : v.bp_controlled ? 'Yes' : 'No'}</strong>
                    </span>
                    <span>
                      Risk: <strong>{v.risk_level ? humanize(v.risk_level) : '—'}</strong>
                    </span>
                    <span>
                      Class: <strong>{v.hypertension_class ? humanize(v.hypertension_class) : '—'}</strong>
                    </span>
                    <span>
                      Followed CDSS advice: <strong>{v.adherent_to_cdss === null ? '—' : v.adherent_to_cdss ? 'Yes' : 'No'}</strong>
                    </span>
                  </div>
                  {v.cdss_recommended_action && (
                    <div className="dash-visit-card-body" style={{ marginTop: 6 }}>
                      <span>Recommended: <strong>{v.cdss_recommended_action}</strong></span>
                    </div>
                  )}
                  {v.medications.length > 0 && (
                    <div className="dash-patient-chips" style={{ marginTop: 6, marginBottom: 0 }}>
                      {v.medications.map((m, i) => (
                        <span key={i} className="dash-chip">{m.drug_name}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="modal-footer-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
