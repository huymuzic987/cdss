import { ClipboardList, HeartPulse, Search, ShieldCheck } from 'lucide-react'
import { memo, useMemo } from 'react'
import { SHOWCASE_PATIENTS, formatBloodPressure, type ShowcasePatient } from './showcasePatients'

export function ClinicMark() {
  return (
    <div className="sc-clinic-mark" aria-label="CDSS Showcase">
      <span className="sc-mark-symbol"><HeartPulse size={20} strokeWidth={2.2} /></span>
      <span><strong>CDSS Showcase</strong></span>
    </div>
  )
}

const PatientCard = memo(function PatientCard({ patient, selected, onSelect }: {
  patient: ShowcasePatient
  selected: boolean
  onSelect: (patient: ShowcasePatient) => void
}) {
  return (
    <button type="button" className={`sc-patient-card${selected ? ' selected' : ''}`}
      onClick={() => onSelect(patient)} data-patient-id={patient.id}
      aria-pressed={selected}>
      <span className={`sc-avatar priority-${patient.priority}`}>{patient.initials}</span>
      <span className="sc-patient-card-body">
        <strong>{patient.name}</strong>
        <small>{patient.form.age ? `${patient.form.age} years · ` : ''}{patient.visitType}</small>
        <span className="sc-card-measure">
          <span>{formatBloodPressure(patient.form.current_clinic_sbp, patient.form.current_clinic_dbp)} <small>mmHg</small></span>
          <em className={`priority-${patient.priority}`}>{patient.status}</em>
        </span>
      </span>
    </button>
  )
})

export function PatientQueue({ selectedId, query, onQueryChange, onSelect }: {
  selectedId: string | null
  query: string
  onQueryChange: (value: string) => void
  onSelect: (patient: ShowcasePatient) => void
}) {
  const patients = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return SHOWCASE_PATIENTS
    return SHOWCASE_PATIENTS.filter((patient) =>
      `${patient.name} ${patient.presetId} ${patient.visitType}`.toLowerCase().includes(normalized),
    )
  }, [query])

  return (
    <aside className="sc-patient-queue" aria-label="Preset patients">
      <div className="sc-queue-heading">
        <span className="sc-eyebrow">Mock patient presets</span>
        <div><h1>Patients</h1><span>{SHOWCASE_PATIENTS.length} presets</span></div>
      </div>
      <label className="sc-search">
        <Search size={17} aria-hidden="true" />
        <span className="sr-only">Search patient presets</span>
        <input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Search presets" />
      </label>
      <div className="sc-queue-list">
        {patients.map((patient) => (
          <PatientCard key={patient.id} patient={patient} selected={selectedId === patient.id} onSelect={onSelect} />
        ))}
        {patients.length === 0 && <p className="sc-no-results">No presets match this search.</p>}
      </div>
    </aside>
  )
}

export function EmptyChart() {
  return (
    <main className="sc-empty-chart">
      <div className="sc-empty-illustration" aria-hidden="true">
        <span><ClipboardList size={38} /></span><i /><i /><i />
      </div>
      <span className="sc-eyebrow">Clinical workspace</span>
      <h2>Select a preset patient to open their chart</h2>
      <p>The patient summary will open here and the CDSS will review the preset’s clinical data automatically.</p>
      <div className="sc-empty-note"><ShieldCheck size={18} /> Recommendations use the live clinical decision support service.</div>
    </main>
  )
}
