import type { DashboardFilters } from '../api/types'
import { fhirPatientExportUrl } from '../api/client'

export type SeedSource = 'preset' | 'synthetic' | 'real_test_case'

interface SeedControlsProps {
  seeding: SeedSource | null
  onSeed: (source: SeedSource) => void
  filters: DashboardFilters
}

export function SeedControls({ seeding, onSeed, filters }: SeedControlsProps) {
  return (
    <div className="dash-seed-controls">
      <button type="button" disabled={seeding !== null} onClick={() => onSeed('real_test_case')} className="dash-btn">
        {seeding === 'real_test_case' ? 'Loading…' : 'Load real reference patients'}
      </button>
      <button type="button" disabled={seeding !== null} onClick={() => onSeed('preset')} className="dash-btn">
        {seeding === 'preset' ? 'Loading…' : 'Load preset patients'}
      </button>
      <button type="button" disabled={seeding !== null} onClick={() => onSeed('synthetic')} className="dash-btn">
        {seeding === 'synthetic' ? 'Loading…' : 'Load 1000 synthetic patients'}
      </button>
      <a className="dash-btn dash-btn-link" href={fhirPatientExportUrl(filters)} target="_blank" rel="noreferrer">
        Export cohort as FHIR
      </a>
    </div>
  )
}
