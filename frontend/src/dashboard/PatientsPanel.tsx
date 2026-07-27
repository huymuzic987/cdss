import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { fetchPatients } from '../api/client'
import type { PatientListItem, PatientSearchParams } from '../api/types'
import { humanize } from './humanize'

const PAGE_SIZE = 10

interface PatientsPanelProps {
  onSelect: (fhirId: string) => void
  /** Bumped by chart clicks elsewhere on the dashboard to jump here with a
   * status filter pre-applied (e.g. clicking the "overdue" KPI tile). */
  presetStatus?: PatientSearchParams['status']
}

export function PatientsPanel({ onSelect, presetStatus }: PatientsPanelProps) {
  const [query, setQuery] = useState('')
  const [gender, setGender] = useState('')
  const [status, setStatus] = useState<PatientSearchParams['status'] | ''>(presetStatus ?? '')
  const [page, setPage] = useState(0)
  const [result, setResult] = useState<{ items: PatientListItem[]; total: number } | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (presetStatus) {
      setStatus(presetStatus)
      setPage(0)
    }
  }, [presetStatus])

  // Debounced so typing a patient ID doesn't fire a request per keystroke.
  useEffect(() => {
    setLoading(true)
    const handle = setTimeout(() => {
      fetchPatients({
        q: query || undefined,
        gender: gender || undefined,
        status: status || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
        .then(setResult)
        .finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(handle)
  }, [query, gender, status, page])

  const totalPages = result ? Math.max(1, Math.ceil(result.total / PAGE_SIZE)) : 1

  return (
    <div>
      <div className="dash-patient-search">
        <div className="dash-search-box">
          <svg
            className="dash-search-icon"
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            className="dash-search-input"
            type="text"
            placeholder="Search by patient ID or department..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(0)
            }}
          />
          {query && (
            <button
              type="button"
              className="dash-search-clear"
              onClick={() => {
                setQuery('')
                setPage(0)
              }}
              aria-label="Clear search"
            >
              <X size={11} />
            </button>
          )}
        </div>
        <select
          className="dash-search-select"
          value={gender}
          onChange={(e) => {
            setGender(e.target.value)
            setPage(0)
          }}
        >
          <option value="">All genders</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
        </select>
        <select
          className="dash-search-select"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as PatientSearchParams['status'])
            setPage(0)
          }}
        >
          <option value="">Any status</option>
          <option value="overdue">Overdue</option>
          <option value="bp_not_controlled">BP not controlled</option>
          <option value="early_revisit">Recent early revisit</option>
        </select>
      </div>

      {result && result.items.length === 0 && !loading && (
        <p className="dash-empty">No patients match this search.</p>
      )}

      {result && result.items.length > 0 && (
        <div className="dash-table-wrap">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Department</th>
                <th>Gender</th>
                <th>Visits</th>
                <th>Last seen</th>
                <th>Last BP</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {result.items.map((p) => (
                <tr key={p.fhir_id}>
                  <td>
                    <button type="button" className="dash-table-row-btn" onClick={() => onSelect(p.fhir_id)}>
                      {p.fhir_id}
                    </button>
                  </td>
                  <td>{p.department ?? '—'}</td>
                  <td>{p.gender ? humanize(p.gender) : '—'}</td>
                  <td>{p.visit_count}</td>
                  <td>{p.last_visit_date ?? '—'}</td>
                  <td>
                    {p.last_bp_controlled === null
                      ? '—'
                      : p.last_bp_controlled
                        ? 'Controlled'
                        : 'Not controlled'}
                  </td>
                  <td>{p.last_risk_level ? humanize(p.last_risk_level) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result && result.total > PAGE_SIZE && (
        <div className="dash-pagination">
          <button
            type="button"
            className="dash-btn dash-btn-small"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <span>
            Page {page + 1} of {totalPages} · {result.total} patients
          </span>
          <button
            type="button"
            className="dash-btn dash-btn-small"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
