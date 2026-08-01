import { HeartPulse, Stethoscope } from 'lucide-react'
import { useState } from 'react'
import type { JsonObject } from '../api/types'
import { BloodPressureSection } from './mockPatientForm/BloodPressureSection'
import { CareSettingSection } from './mockPatientForm/CareSettingSection'
import { ComorbiditiesSection } from './mockPatientForm/ComorbiditiesSection'
import { DemographicsSection } from './mockPatientForm/DemographicsSection'
import { SectionHeader } from './mockPatientForm/FormControls'
import { bundleToForm } from './mockPatientForm/payload'
import { SimulatorFooter, SimulatorHeader } from './mockPatientForm/SimulatorChrome'
import { DEFAULT_FORM, type PatientFormData } from './mockPatientForm/types'
import { validatePatientForm } from './mockPatientForm/validation'
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

export function MockPatientSidebar(props: MockPatientSidebarProps) {
  const [form, setForm] = useState<PatientFormData>(DEFAULT_FORM)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [selectedPresetId, setSelectedPresetId] = useState('')
  const [selectedPresetBundle, setSelectedPresetBundle] = useState<JsonObject | null>(null)
  const [openSections, setOpenSections] = useState({ bp: true, demographics: true, comorbidities: true, care: true })
  const toggleSection = (key: keyof typeof openSections) =>
    setOpenSections((previous) => ({ ...previous, [key]: !previous[key] }))

  const setField = <K extends keyof PatientFormData>(key: K, value: PatientFormData[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }))
    setSelectedPresetBundle(null)
    setValidationError(null)
  }
  const setStr = (key: keyof PatientFormData, value: string) =>
    setField(key, value as PatientFormData[typeof key])
  const setBool = (key: keyof PatientFormData, value: boolean) =>
    setField(key, value as PatientFormData[typeof key])

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId)
    setValidationError(null)
    const preset = PATIENT_PRESETS.find((candidate) => candidate.id === presetId)
    setSelectedPresetBundle(preset?.bundle ?? null)
    setForm(preset ? bundleToForm(preset.bundle) : DEFAULT_FORM)
  }

  const start = (manual: boolean) => {
    const validation = validatePatientForm(form)
    setValidationError(validation.error)
    if (!validation.payload) return
    const callback = manual ? props.onManualStart : props.onStart
    // A confirmed acute scenario always outranks the ordinary diagnosis and
    // pregnancy entry points.  Do not require the separate summary flag here:
    // emergency presets are themselves the evidence of acute target-organ
    // involvement, and that summary flag may be absent in imported bundles.
    const hasEmergencyScenario = selectedPresetId.startsWith('emergency-') || (
      form.has_hypertensive_encephalopathy
      || form.has_acute_ischemic_stroke
      || form.has_acute_intracerebral_hemorrhage
      || form.has_acute_coronary_syndrome
      || form.has_acute_cardiogenic_pulmonary_edema
      || form.has_acute_aortic_syndrome
      || form.has_eclampsia_severe_preeclampsia_or_hellp
      || form.has_tma_or_acute_kidney_injury
    )
    const startTreeKey = form.medication_follow_up_stage !== ''
      ? 'treatment-threshold-and-bp-target'
      : hasEmergencyScenario ? 'hypertensive-emergency' : 'hypertension-diagnosis'
    callback(startTreeKey, selectedPresetBundle ?? validation.payload)
  }

  const reset = () => {
    setForm(DEFAULT_FORM)
    setValidationError(null)
    setSelectedPresetId('')
    setSelectedPresetBundle(null)
    props.onReset()
  }

  return (
    <aside className="ps-sidebar">
      <SimulatorHeader theme={props.theme} onToggleTheme={props.onToggleTheme} />
      <div className="ps-starting-tree">
        <label className="ps-field-label" htmlFor="preset-select">Preset Patient</label>
        <select
          id="preset-select"
          className="ps-select"
          value={selectedPresetId}
          onChange={(event) => handlePresetChange(event.target.value)}
          disabled={props.isRunning}
        >
          <option value="">— Select a preset —</option>
          {Array.from(new Set(PATIENT_PRESETS.map((preset) => preset.category))).map((category) => (
            <optgroup key={category} label={category}>
              {PATIENT_PRESETS.filter((preset) => preset.category === category).map((preset) => (
                <option key={preset.id} value={preset.id} title={preset.description}>{preset.label}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
      <div className="ps-body">
        <SectionHeader label="Blood Pressure" icon={<Stethoscope size={13} />} open={openSections.bp} onToggle={() => toggleSection('bp')} />
        {openSections.bp && <BloodPressureSection form={form} setStr={setStr} setBool={setBool} disabled={props.isRunning} />}
        <SectionHeader label="Demographics & Risk" icon="👤" open={openSections.demographics} onToggle={() => toggleSection('demographics')} />
        {openSections.demographics && <DemographicsSection form={form} setStr={setStr} setBool={setBool} disabled={props.isRunning} />}
        <SectionHeader label="Comorbidities & Clinical Flags" icon={<HeartPulse size={13} />} open={openSections.comorbidities} onToggle={() => toggleSection('comorbidities')} />
        {openSections.comorbidities && <ComorbiditiesSection form={form} setStr={setStr} setBool={setBool} disabled={props.isRunning} />}
        <SectionHeader label="Care Setting & Follow-Up" icon="⚙️" open={openSections.care} onToggle={() => toggleSection('care')} />
        {openSections.care && <CareSettingSection form={form} setStr={setStr} setBool={setBool} disabled={props.isRunning} />}
        <div style={{ height: 16 }} />
      </div>
      <SimulatorFooter
        isRunning={props.isRunning}
        canReset={props.canReset}
        validationError={validationError}
        onStart={() => start(false)}
        onManualStart={() => start(true)}
        onReset={reset}
      />
    </aside>
  )
}
