import { AlertTriangle, FlaskConical, HeartPulse, Moon, MousePointer2, Play, Stethoscope, Sun, X } from 'lucide-react'
import { useState } from 'react'
import type { JsonObject } from '../api/types'
import { BloodPressureSection } from './mockPatientForm/BloodPressureSection'
import { CareSettingSection } from './mockPatientForm/CareSettingSection'
import { ComorbiditiesSection } from './mockPatientForm/ComorbiditiesSection'
import { DemographicsSection } from './mockPatientForm/DemographicsSection'
import { SectionHeader } from './mockPatientForm/FormControls'
import { formToPayload } from './mockPatientForm/payload'
import { DEFAULT_FORM, type PatientFormData } from './mockPatientForm/types'
import { PATIENT_PRESETS } from './patientPresets'

export type { PatientFormData } from './mockPatientForm/types'

interface MockPatientSidebarProps {
  isRunning: boolean
  canReset: boolean
  onStart: (startTreeKey: string, input: JsonObject) => void
  onManualStart: (startTreeKey: string, input: JsonObject) => void
  onReset: () => void
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export function MockPatientSidebar({ isRunning, canReset, onStart, onManualStart, onReset, theme, onToggleTheme }: MockPatientSidebarProps) {
  const [form, setForm] = useState<PatientFormData>(DEFAULT_FORM)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [selectedPresetId, setSelectedPresetId] = useState('')
  const [openSections, setOpenSections] = useState({ bp: true, demographics: true, comorbidities: true, care: true })
  const toggleSection = (key: keyof typeof openSections) =>
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }))

  const setField = <K extends keyof PatientFormData>(key: K, value: PatientFormData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    // Clear validation error when user types/changes fields
    setValidationError(null)
  }

  const setStr = (key: keyof PatientFormData, value: string) => setField(key, value as PatientFormData[typeof key])
  const setBool = (key: keyof PatientFormData, value: boolean) => setField(key, value as PatientFormData[typeof key])

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId)
    setValidationError(null)
    if (!presetId) {
      setForm(DEFAULT_FORM)
      return
    }
    const preset = PATIENT_PRESETS.find((p) => p.id === presetId)
    if (preset) setForm({ ...DEFAULT_FORM, ...preset.data })
  }

  /** Validate essential minimum data to prevent backend missing path errors.
   * Returns the built payload, or null (after flagging validationError) if invalid. */
  const validateAndBuildPayload = (): JsonObject | null => {
    const s1 = parseFloat(form.clinic_1_sbp)
    const d1 = parseFloat(form.clinic_1_dbp)
    const ageVal = parseFloat(form.age)
    const riskVal = parseFloat(form.risk_factor_count)

    if (!form.clinic_1_sbp || !form.clinic_1_dbp || isNaN(s1) || isNaN(d1) || s1 <= 0 || d1 <= 0) {
      setValidationError('Clinic SBP and DBP are required positive numbers.')
      return null
    }
    if (!form.age || isNaN(ageVal) || ageVal <= 0) {
      setValidationError('Age is required and must be a valid positive number.')
      return null
    }
    if (!form.risk_factor_count || isNaN(riskVal) || riskVal < 0) {
      setValidationError('Risk Factor Count is required and must be 0 or higher.')
      return null
    }
    if (form.is_medication_follow_up) {
      const targetSbp = parseFloat(form.target_sbp_upper)
      const targetDbp = parseFloat(form.target_dbp_upper)
      if (!form.target_sbp_upper || !form.target_dbp_upper || isNaN(targetSbp) || isNaN(targetDbp) || targetSbp <= 0 || targetDbp <= 0) {
        setValidationError('Target SBP and DBP are required for medication follow-up visits.')
        return null
      }
    }

    setValidationError(null)
    return formToPayload(form)
  }

  /** Tree 1 (initial diagnosis) has no awareness of follow-up visits. Follow-up
   * patients must enter at Tree 3, which reads is_lifestyle_follow_up /
   * is_medication_follow_up directly. */
  const startTreeKey = form.is_lifestyle_follow_up || form.is_medication_follow_up
    ? 'treatment-threshold-and-bp-target'
    : 'hypertension-diagnosis'

  const handleStart = () => {
    const payload = validateAndBuildPayload()
    if (!payload) return
    onStart(startTreeKey, payload)
  }

  const handleManualStart = () => {
    const payload = validateAndBuildPayload()
    if (!payload) return
    onManualStart(startTreeKey, payload)
  }

  const handleReset = () => {
    setForm(DEFAULT_FORM)
    setValidationError(null)
    setSelectedPresetId('')
    onReset()
  }

  return (
    <aside className="ps-sidebar">
      {/* ---- Sticky header ---- */}
      <div className="ps-header">
        <div className="ps-header-left">
          <span className="ps-header-icon"><FlaskConical size={16} /></span>
          <div>
            <div className="ps-header-title">Patient Simulator</div>
            <div className="ps-header-sub">Fill in fields to simulate traversal</div>
          </div>
        </div>
        <button
          type="button"
          className="ps-theme-toggle"
          onClick={onToggleTheme}
          title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
        </button>
      </div>

      {/* ---- Preset patient selector (sticky below header) ---- */}
      <div className="ps-starting-tree">
        <label className="ps-field-label" htmlFor="preset-select">Preset Patient</label>
        <select
          id="preset-select"
          className="ps-select"
          value={selectedPresetId}
          onChange={(e) => handlePresetChange(e.target.value)}
          disabled={isRunning}
        >
          <option value="">— Select a preset —</option>
          {Array.from(new Set(PATIENT_PRESETS.map((p) => p.category))).map((category) => (
            <optgroup key={category} label={category}>
              {PATIENT_PRESETS.filter((p) => p.category === category).map((p) => (
                <option key={p.id} value={p.id} title={p.description}>
                  {p.label}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {/* ---- Scrollable form body ---- */}
      <div className="ps-body">

        {/* ========== SECTION 1: Blood Pressure ========== */}
        <SectionHeader label="Blood Pressure" icon={<Stethoscope size={13} />} open={openSections.bp} onToggle={() => toggleSection('bp')} />
        {openSections.bp && (
          <BloodPressureSection form={form} setStr={setStr} setBool={setBool} disabled={isRunning} />
        )}

        {/* ========== SECTION 2: Demographics ========== */}
        <SectionHeader label="Demographics & Risk" icon="👤" open={openSections.demographics} onToggle={() => toggleSection('demographics')} />
        {openSections.demographics && (
          <DemographicsSection form={form} setStr={setStr} setBool={setBool} disabled={isRunning} />
        )}

        {/* ========== SECTION 3: Comorbidities ========== */}
        <SectionHeader label="Comorbidities & Clinical Flags" icon={<HeartPulse size={13} />} open={openSections.comorbidities} onToggle={() => toggleSection('comorbidities')} />
        {openSections.comorbidities && (
          <ComorbiditiesSection form={form} setStr={setStr} setBool={setBool} disabled={isRunning} />
        )}

        {/* ========== SECTION 4: Care Setting ========== */}
        <SectionHeader label="Care Setting & Follow-Up" icon="⚙️" open={openSections.care} onToggle={() => toggleSection('care')} />
        {openSections.care && (
          <CareSettingSection form={form} setStr={setStr} setBool={setBool} disabled={isRunning} />
        )}

        {/* Spacer at bottom so content doesn't hide under footer */}
        <div style={{ height: 16 }} />
      </div>

      {/* ---- Sticky footer ---- */}
      <div className="ps-footer">
        {validationError && (
          <div className="ps-validation-error">
            <AlertTriangle size={13} style={{ flexShrink: 0 }} /> {validationError}
          </div>
        )}
        <button
          type="button"
          className="ps-btn-start"
          onClick={handleStart}
          disabled={isRunning}
        >
          {isRunning ? (
            <><span className="ps-spinner" /> Simulating…</>
          ) : (
            <><Play size={13} /> Start Traversal</>
          )}
        </button>
        <button
          type="button"
          className="ps-btn-manual"
          onClick={handleManualStart}
          disabled={isRunning}
        >
          <MousePointer2 size={13} /> Manual Traverse
        </button>
        <button
          type="button"
          className="ps-btn-reset"
          onClick={handleReset}
          disabled={!canReset}
        >
          <X size={13} /> Reset
        </button>
      </div>
    </aside>
  )
}
