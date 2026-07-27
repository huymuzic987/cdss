import { useState } from 'react'
import type { DashboardFilters } from '../api/types'
import { humanize } from './humanize'

// ICD-10 codes, matching PatientCondition.icd10_code (excludes I10 -- every patient has it).
const COMORBIDITIES = ['E11', 'N18', 'I25', 'I50', 'I63']
const DEPARTMENTS = ['Ngoại trú', 'Cấp cứu', 'Nội thận', 'Nội tim mạch']

interface FiltersBarProps {
  filters: DashboardFilters
  onChange: (filters: DashboardFilters) => void
  onExportCsv?: () => void
}

/** Power-BI-slicer-style filter card: edits are staged locally and only take
 * effect on Apply/Clear/quick-chip click, rather than refetching on every
 * keystroke or selection. */
export function FiltersBar({ filters, onChange, onExportCsv }: FiltersBarProps) {
  const [draft, setDraft] = useState<DashboardFilters>(filters)

  const apply = () => onChange(draft)
  const clear = () => {
    setDraft({})
    onChange({})
  }
  const applyQuickFilter = (patch: DashboardFilters) => {
    const next = { ...draft, ...patch }
    setDraft(next)
    onChange(next)
  }

  return (
    <div className="dash-filters-card">
      <div className="dash-filters-card-header">
        <h3 className="dash-filters-title">Filters</h3>
        <p className="dash-filters-subtitle">Pick cohort conditions like a Power BI slicer -- charts update on Apply.</p>
      </div>

      <div className="dash-filters-grid">
        <label className="dash-filter">
          <span>Department</span>
          <select
            value={draft.department ?? ''}
            onChange={(e) => setDraft({ ...draft, department: e.target.value || undefined })}
          >
            <option value="">All departments</option>
            {DEPARTMENTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label className="dash-filter">
          <span>Min age</span>
          <input
            type="number"
            min={0}
            placeholder="—"
            value={draft.min_age ?? ''}
            onChange={(e) => setDraft({ ...draft, min_age: e.target.value ? Number(e.target.value) : undefined })}
          />
        </label>
        <label className="dash-filter">
          <span>Max age</span>
          <input
            type="number"
            min={0}
            placeholder="—"
            value={draft.max_age ?? ''}
            onChange={(e) => setDraft({ ...draft, max_age: e.target.value ? Number(e.target.value) : undefined })}
          />
        </label>
        <label className="dash-filter">
          <span>Gender</span>
          <select value={draft.gender ?? ''} onChange={(e) => setDraft({ ...draft, gender: e.target.value || undefined })}>
            <option value="">All</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </label>
        <label className="dash-filter">
          <span>Comorbidity (ICD-10)</span>
          <select
            value={draft.comorbidity_icd10 ?? ''}
            onChange={(e) => setDraft({ ...draft, comorbidity_icd10: e.target.value || undefined })}
          >
            <option value="">All patients</option>
            {COMORBIDITIES.map((c) => (
              <option key={c} value={c}>
                {humanize(c)}
              </option>
            ))}
          </select>
        </label>
        <label className="dash-filter">
          <span>CDSS adherence</span>
          <select
            value={draft.adherent_to_cdss === undefined ? '' : String(draft.adherent_to_cdss)}
            onChange={(e) =>
              setDraft({
                ...draft,
                adherent_to_cdss: e.target.value === '' ? undefined : e.target.value === 'true',
              })
            }
          >
            <option value="">All</option>
            <option value="true">Followed advice</option>
            <option value="false">Didn't follow advice</option>
          </select>
        </label>
      </div>

      <div className="dash-filters-actions">
        <button type="button" className="dash-btn" onClick={apply}>
          Apply
        </button>
        <button type="button" className="dash-btn dash-btn-link" onClick={clear}>
          Clear filters
        </button>
        <button type="button" className="dash-btn dash-btn-small" onClick={() => applyQuickFilter({ min_age: 65 })}>
          Quick: age ≥ 65
        </button>
        <button
          type="button"
          className="dash-btn dash-btn-small"
          onClick={() => applyQuickFilter({ comorbidity_icd10: 'N18' })}
        >
          Quick: kidney failure (N18)
        </button>
        {onExportCsv && (
          <button type="button" className="dash-btn dash-btn-small dash-filters-export" onClick={onExportCsv}>
            Export cohort stats CSV
          </button>
        )}
      </div>
    </div>
  )
}
