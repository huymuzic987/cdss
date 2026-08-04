import { Moon, Sun } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { evaluateFollowUp, evaluateTree } from '../api/client'
import type { ApiErrorResponse, EvaluationResponse } from '../api/types'
import { TraversalResultModal } from '../panels/TraversalResultModal'
import { PatientChart, type EvaluationStatus } from './PatientChart'
import { ClinicMark, EmptyChart, PatientQueue } from './ShowcaseChrome'
import type { ShowcasePatient } from './showcasePatients'
import { useShowcaseTheme } from './useShowcaseTheme'
import './showcase.css'

export function ShowcasePage() {
  const [selectedPatient, setSelectedPatient] = useState<ShowcasePatient | null>(null)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<EvaluationStatus>('idle')
  const [result, setResult] = useState<EvaluationResponse | null>(null)
  const [partial, setPartial] = useState<ApiErrorResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const { theme, toggleTheme } = useShowcaseTheme()
  const runIdRef = useRef(0)

  const runEvaluation = useCallback(async (patient: ShowcasePatient) => {
    const runId = ++runIdRef.current
    setStatus('loading'); setResult(null); setPartial(null); setError(null); setShowModal(false)
    try {
      const response = patient.evaluationMode === 'follow-up'
        ? await evaluateFollowUp(patient.bundle) : await evaluateTree(patient.bundle)
      if (runIdRef.current !== runId) return
      if (response.error) { setStatus('error'); setError(response.error.message); return }
      setResult(response.result); setPartial(response.partial); setStatus('success'); setShowModal(true)
    } catch (requestError) {
      if (runIdRef.current !== runId) return
      setStatus('error')
      setError(requestError instanceof Error ? requestError.message : 'The clinical service could not be reached.')
    }
  }, [])

  useEffect(() => () => { runIdRef.current += 1 }, [])
  const selectPatient = useCallback((patient: ShowcasePatient) => {
    setSelectedPatient(patient)
    void runEvaluation(patient)
  }, [runEvaluation])
  const closeModal = () => {
    setShowModal(false)
    window.setTimeout(() => selectedPatient
      && document.querySelector<HTMLElement>(`[data-patient-id="${selectedPatient.id}"]`)?.focus(), 0)
  }

  return (
    <div className="showcase-shell" data-showcase-theme={theme}>
      <header className="sc-topbar">
        <ClinicMark />
        <div className="sc-topbar-title"><strong>Clinical workspace</strong><span>Patient review and decision support</span></div>
        <button type="button" className="sc-theme-toggle" onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
          {theme === 'dark' ? <Sun size={19} /> : <Moon size={19} />}
        </button>
      </header>
      <PatientQueue selectedId={selectedPatient?.id ?? null} query={query} onQueryChange={setQuery} onSelect={selectPatient} />
      {selectedPatient ? <PatientChart patient={selectedPatient} status={status} error={error}
        hasRecommendation={Boolean(result || partial)} onRetry={() => void runEvaluation(selectedPatient)}
        onViewRecommendation={() => setShowModal(true)} /> : <EmptyChart />}
      {showModal && <TraversalResultModal result={result} partial={partial} onClose={closeModal} locale="en" />}
    </div>
  )
}
