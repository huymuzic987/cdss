import type { DashboardFilters } from '../api/types'
import { humanize } from './humanize'

// ICD-10 codes, matching PatientCondition.icd10_code (excludes I10 -- every patient has it).
const COMORBIDITIES = ['E11', 'N18', 'I25', 'I50', 'I63']

interface FiltersBarProps {
  filters: DashboardFilters
  onChange: (filters: DashboardFilters) => void
}

export function FiltersBar({ filters, onChange }: FiltersBarProps) {
  return (
    <div className="dash-filters-row">
      <label className="dash-filter">
        <span>Facility</span>
        <select
          value={filters.facility_capability ?? ''}
          onChange={(e) => onChange({ ...filters, facility_capability: e.target.value || undefined })}
        >
          <option value="">All facilities</option>
          <option value="FULL_RESOURCES">Full resources</option>
          <option value="LIMITED_RESOURCES">Limited resources</option>
        </select>
      </label>
      <label className="dash-filter">
        <span>Comorbidity</span>
        <select
          value={filters.comorbidity_icd10 ?? ''}
          onChange={(e) => onChange({ ...filters, comorbidity_icd10: e.target.value || undefined })}
        >
          <option value="">All patients</option>
          {COMORBIDITIES.map((c) => (
            <option key={c} value={c}>
              {humanize(c)}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
