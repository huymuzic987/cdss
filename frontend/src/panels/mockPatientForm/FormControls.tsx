import type { ReactNode } from 'react'
import type { PatientFormData } from './types'

// ---------------------------------------------------------------------------
// Shared, presentation-only form controls
// ---------------------------------------------------------------------------

export function SectionHeader({
  label,
  icon,
  open,
  onToggle,
}: {
  label: string
  icon: ReactNode
  open: boolean
  onToggle: () => void
}) {
  return (
    <button type="button" className="ps-section-header" onClick={onToggle} aria-expanded={open}>
      <span className="ps-section-icon">{icon}</span>
      <span className="ps-section-label">{label}</span>
      <svg
        className={`ps-section-chevron${open ? ' open' : ''}`}
        width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M9 18l6-6-6-6"/>
      </svg>
    </button>
  )
}

interface BpRowProps {
  label: string
  sbpKey: keyof PatientFormData
  dbpKey: keyof PatientFormData
  form: PatientFormData
  onChange: (k: keyof PatientFormData, v: string) => void
  disabled?: boolean
}

export function BpRow({ label, sbpKey, dbpKey, form, onChange, disabled }: BpRowProps) {
  return (
    <div className="ps-bp-row">
      <span className="ps-bp-label">{label}</span>
      <input
        className="ps-bp-input"
        type="number"
        placeholder="SBP"
        min={60} max={300}
        value={form[sbpKey] as string}
        onChange={(e) => onChange(sbpKey, e.target.value)}
        disabled={disabled}
      />
      <span className="ps-bp-sep">/</span>
      <input
        className="ps-bp-input"
        type="number"
        placeholder="DBP"
        min={40} max={200}
        value={form[dbpKey] as string}
        onChange={(e) => onChange(dbpKey, e.target.value)}
        disabled={disabled}
      />
      <span className="ps-bp-unit">mmHg</span>
    </div>
  )
}

interface ToggleProps {
  label: string
  fieldKey: keyof PatientFormData
  form: PatientFormData
  onChange: (k: keyof PatientFormData, v: boolean) => void
  disabled?: boolean
  note?: string
}

export function Toggle({ label, fieldKey, form, onChange, disabled, note }: ToggleProps) {
  const checked = form[fieldKey] as boolean
  return (
    <label className={`ps-toggle${disabled ? ' ps-toggle-disabled' : ''}`}>
      <span className="ps-toggle-text">
        {label}
        {note && <span className="ps-toggle-note">{note}</span>}
      </span>
      <span
        className={`ps-toggle-track${checked ? ' checked' : ''}`}
        onClick={() => !disabled && onChange(fieldKey, !checked)}
      >
        <span className="ps-toggle-thumb" />
      </span>
    </label>
  )
}
