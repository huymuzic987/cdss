import { AlertTriangle, FlaskConical, HeartPulse, Moon, MousePointer2, Play, Settings2, Stethoscope, Sun, User, X } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import type { JsonObject } from '../api/types'
import { PATIENT_PRESETS } from './patientPresets'

// ---------------------------------------------------------------------------
// Form state definition
// ---------------------------------------------------------------------------

export interface PatientFormData {
  // BP — initial clinic
  clinic_1_sbp: string
  clinic_1_dbp: string
  clinic_2_sbp: string
  clinic_2_dbp: string
  clinic_3_sbp: string
  clinic_3_dbp: string
  // BP — follow-up
  current_clinic_sbp: string
  current_clinic_dbp: string
  pre_lifestyle_clinic_sbp: string
  pre_lifestyle_clinic_dbp: string
  // BP — out-of-office
  home_sbp: string
  home_dbp: string
  daytime_sbp: string
  daytime_dbp: string
  morning_sbp: string
  morning_dbp: string
  bp_24h_sbp: string
  bp_24h_dbp: string
  // Demographics
  age: string
  risk_factor_count: string
  is_pregnant: boolean
  // Comorbidities
  has_coronary_artery_disease: boolean
  has_type_2_diabetes: boolean
  has_heart_failure: boolean
  has_ckd: boolean
  has_ckd_stage_3_or_higher: boolean
  has_diabetes: boolean
  has_cardiovascular_disease: boolean
  has_stroke: boolean
  has_tia: boolean
  has_frailty_syndrome: boolean
  has_target_organ_damage: boolean
  // Coronary artery disease detail (hypertension-coronary-artery-disease)
  has_mi_acs: boolean
  has_ccs_angina: boolean
  has_ccs_revasc: boolean
  has_cabg: boolean
  // Heart failure detail (hypertension-heart-failure)
  has_hfref: boolean
  has_hfmref: boolean
  has_hfpef: boolean
  has_lvh: boolean
  bp_target_reached: boolean
  // Chronic kidney disease detail (hypertension-chronic-kidney-disease)
  has_kidney_transplant: boolean
  has_prior_creatinine_test: boolean
  still_using_ras_inhibitor: boolean
  creatinine_increased_over_30_percent: boolean
  // Resistant hypertension detail (resistant-hypertension, limited-resources branch)
  tolerates_mra: boolean
  tolerates_spironolactone: boolean
  // Hypertensive emergency detail (hypertensive-emergency)
  has_acute_ischemic_stroke: boolean
  is_thrombolysis_candidate: boolean
  has_acute_coronary_syndrome: boolean
  has_acute_cardiogenic_pulmonary_edema: boolean
  has_acute_aortic_syndrome: boolean
  has_eclampsia_severe_preeclampsia_or_hellp: boolean
  has_hypertensive_encephalopathy: boolean
  has_acute_intracerebral_hemorrhage: boolean
  // Pregnancy detail (hypertension-in-pregnancy)
  has_pre_pregnancy_hypertension: boolean
  has_hypertension_before_week_20: boolean
  has_hypertension_after_week_20: boolean
  has_prior_gestational_hypertension: boolean
  has_high_preeclampsia_risk: boolean
  has_proteinuria: boolean
  proteinuria_24h_mg: string
  acr_mg_mmol: string
  has_autoimmune_disease: boolean
  has_severe_headache: boolean
  has_visual_disturbance: boolean
  has_epigastric_pain: boolean
  has_hemolysis: boolean
  has_elevated_liver_enzymes: boolean
  has_low_platelets: boolean
  has_seizure: boolean
  has_pulmonary_edema: boolean
  has_coagulopathy: boolean
  has_hypertensive_crisis: boolean
  is_treatment_target_not_achieved: boolean
  is_postpartum: boolean
  is_breastfeeding: boolean
  weeks_persisting_postpartum: string
  weeks_resolved_postpartum: string
  // Care setting
  facility_capability: 'FULL_RESOURCES' | 'LIMITED_RESOURCES' | ''
  is_lifestyle_follow_up: boolean
  is_medication_follow_up: boolean
  medication_follow_up_stage: 'INITIAL_REGIMEN' | 'ESCALATED_REGIMEN' | ''
  // Active BP target
  has_active_bp_target: boolean
  target_sbp_upper: string
  target_dbp_upper: string
}

const DEFAULT_FORM: PatientFormData = {
  clinic_1_sbp: '', clinic_1_dbp: '',
  clinic_2_sbp: '', clinic_2_dbp: '',
  clinic_3_sbp: '', clinic_3_dbp: '',
  current_clinic_sbp: '', current_clinic_dbp: '',
  pre_lifestyle_clinic_sbp: '', pre_lifestyle_clinic_dbp: '',
  home_sbp: '', home_dbp: '',
  daytime_sbp: '', daytime_dbp: '',
  morning_sbp: '', morning_dbp: '',
  bp_24h_sbp: '', bp_24h_dbp: '',
  age: '',
  risk_factor_count: '',
  is_pregnant: false,
  has_coronary_artery_disease: false,
  has_type_2_diabetes: false,
  has_heart_failure: false,
  has_ckd: false,
  has_ckd_stage_3_or_higher: false,
  has_diabetes: false,
  has_cardiovascular_disease: false,
  has_stroke: false,
  has_tia: false,
  has_frailty_syndrome: false,
  has_target_organ_damage: false,
  has_mi_acs: false,
  has_ccs_angina: false,
  has_ccs_revasc: false,
  has_cabg: false,
  has_hfref: false,
  has_hfmref: false,
  has_hfpef: false,
  has_lvh: false,
  bp_target_reached: false,
  has_kidney_transplant: false,
  has_prior_creatinine_test: false,
  still_using_ras_inhibitor: false,
  creatinine_increased_over_30_percent: false,
  tolerates_mra: false,
  tolerates_spironolactone: false,
  has_acute_ischemic_stroke: false,
  is_thrombolysis_candidate: false,
  has_acute_coronary_syndrome: false,
  has_acute_cardiogenic_pulmonary_edema: false,
  has_acute_aortic_syndrome: false,
  has_eclampsia_severe_preeclampsia_or_hellp: false,
  has_hypertensive_encephalopathy: false,
  has_acute_intracerebral_hemorrhage: false,
  has_pre_pregnancy_hypertension: false,
  has_hypertension_before_week_20: false,
  has_hypertension_after_week_20: false,
  has_prior_gestational_hypertension: false,
  has_high_preeclampsia_risk: false,
  has_proteinuria: false,
  proteinuria_24h_mg: '',
  acr_mg_mmol: '',
  has_autoimmune_disease: false,
  has_severe_headache: false,
  has_visual_disturbance: false,
  has_epigastric_pain: false,
  has_hemolysis: false,
  has_elevated_liver_enzymes: false,
  has_low_platelets: false,
  has_seizure: false,
  has_pulmonary_edema: false,
  has_coagulopathy: false,
  has_hypertensive_crisis: false,
  is_treatment_target_not_achieved: false,
  is_postpartum: false,
  is_breastfeeding: false,
  weeks_persisting_postpartum: '',
  weeks_resolved_postpartum: '',
  facility_capability: '',
  is_lifestyle_follow_up: false,
  is_medication_follow_up: false,
  medication_follow_up_stage: '',
  has_active_bp_target: false,
  target_sbp_upper: '',
  target_dbp_upper: '',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert string to number or omit if empty */
function num(v: string): number | undefined {
  const n = parseFloat(v)
  return isNaN(n) ? undefined : n
}

function formToPayload(form: PatientFormData): JsonObject {
  const out: JsonObject = {}

  const set = (key: string, v: number | boolean | string | JsonObject | undefined) => {
    if (v === undefined || v === '' || v === false) return
    out[key] = v
  }

  // BP clinic
  set('clinic_1_sbp', num(form.clinic_1_sbp))
  set('clinic_1_dbp', num(form.clinic_1_dbp))
  set('clinic_2_sbp', num(form.clinic_2_sbp))
  set('clinic_2_dbp', num(form.clinic_2_dbp))
  set('clinic_3_sbp', num(form.clinic_3_sbp))
  set('clinic_3_dbp', num(form.clinic_3_dbp))
  // BP follow-up
  set('current_clinic_sbp', num(form.current_clinic_sbp))
  set('current_clinic_dbp', num(form.current_clinic_dbp))
  set('pre_lifestyle_clinic_sbp', num(form.pre_lifestyle_clinic_sbp))
  set('pre_lifestyle_clinic_dbp', num(form.pre_lifestyle_clinic_dbp))
  // BP OOB
  set('home_sbp', num(form.home_sbp))
  set('home_dbp', num(form.home_dbp))
  set('daytime_sbp', num(form.daytime_sbp))
  set('daytime_dbp', num(form.daytime_dbp))
  set('morning_sbp', num(form.morning_sbp))
  set('morning_dbp', num(form.morning_dbp))
  set('bp_24h_sbp', num(form.bp_24h_sbp))
  set('bp_24h_dbp', num(form.bp_24h_dbp))
  // Demographics
  set('age', num(form.age))
  set('risk_factor_count', num(form.risk_factor_count))
  // Booleans — must be explicitly included as true or false so backend JSON path evaluation doesn't fail
  out['is_pregnant'] = form.is_pregnant
  out['has_coronary_artery_disease'] = form.has_coronary_artery_disease
  out['has_type_2_diabetes'] = form.has_type_2_diabetes
  out['has_heart_failure'] = form.has_heart_failure
  out['has_ckd'] = form.has_ckd
  out['has_ckd_stage_3_or_higher'] = form.has_ckd_stage_3_or_higher
  out['has_diabetes'] = form.has_diabetes
  out['has_cardiovascular_disease'] = form.has_cardiovascular_disease
  out['has_stroke'] = form.has_stroke
  out['has_tia'] = form.has_tia
  out['has_frailty_syndrome'] = form.has_frailty_syndrome
  out['has_target_organ_damage'] = form.has_target_organ_damage
  out['has_mi_acs'] = form.has_mi_acs
  out['has_ccs_angina'] = form.has_ccs_angina
  out['has_ccs_revasc'] = form.has_ccs_revasc
  out['has_cabg'] = form.has_cabg
  out['has_hfref'] = form.has_hfref
  out['has_hfmref'] = form.has_hfmref
  out['has_hfpef'] = form.has_hfpef
  out['has_lvh'] = form.has_lvh
  out['bp_target_reached'] = form.bp_target_reached
  out['has_kidney_transplant'] = form.has_kidney_transplant
  out['has_prior_creatinine_test'] = form.has_prior_creatinine_test
  out['still_using_ras_inhibitor'] = form.still_using_ras_inhibitor
  out['creatinine_increased_over_30_percent'] = form.creatinine_increased_over_30_percent
  out['tolerates_mra'] = form.tolerates_mra
  out['tolerates_spironolactone'] = form.tolerates_spironolactone
  out['has_acute_ischemic_stroke'] = form.has_acute_ischemic_stroke
  out['is_thrombolysis_candidate'] = form.is_thrombolysis_candidate
  out['has_acute_coronary_syndrome'] = form.has_acute_coronary_syndrome
  out['has_acute_cardiogenic_pulmonary_edema'] = form.has_acute_cardiogenic_pulmonary_edema
  out['has_acute_aortic_syndrome'] = form.has_acute_aortic_syndrome
  out['has_eclampsia_severe_preeclampsia_or_hellp'] = form.has_eclampsia_severe_preeclampsia_or_hellp
  out['has_hypertensive_encephalopathy'] = form.has_hypertensive_encephalopathy
  out['has_acute_intracerebral_hemorrhage'] = form.has_acute_intracerebral_hemorrhage
  out['has_pre_pregnancy_hypertension'] = form.has_pre_pregnancy_hypertension
  out['has_hypertension_before_week_20'] = form.has_hypertension_before_week_20
  out['has_hypertension_after_week_20'] = form.has_hypertension_after_week_20
  out['has_prior_gestational_hypertension'] = form.has_prior_gestational_hypertension
  out['has_high_preeclampsia_risk'] = form.has_high_preeclampsia_risk
  out['has_proteinuria'] = form.has_proteinuria
  set('proteinuria_24h_mg', num(form.proteinuria_24h_mg))
  set('acr_mg_mmol', num(form.acr_mg_mmol))
  out['has_autoimmune_disease'] = form.has_autoimmune_disease
  out['has_severe_headache'] = form.has_severe_headache
  out['has_visual_disturbance'] = form.has_visual_disturbance
  out['has_epigastric_pain'] = form.has_epigastric_pain
  out['has_hemolysis'] = form.has_hemolysis
  out['has_elevated_liver_enzymes'] = form.has_elevated_liver_enzymes
  out['has_low_platelets'] = form.has_low_platelets
  out['has_seizure'] = form.has_seizure
  out['has_pulmonary_edema'] = form.has_pulmonary_edema
  out['has_coagulopathy'] = form.has_coagulopathy
  out['has_hypertensive_crisis'] = form.has_hypertensive_crisis
  out['is_treatment_target_not_achieved'] = form.is_treatment_target_not_achieved
  out['is_postpartum'] = form.is_postpartum
  out['is_breastfeeding'] = form.is_breastfeeding
  set('weeks_persisting_postpartum', num(form.weeks_persisting_postpartum))
  set('weeks_resolved_postpartum', num(form.weeks_resolved_postpartum))

  // Care setting
  if (form.facility_capability) out['facility_capability'] = form.facility_capability
  out['is_lifestyle_follow_up'] = form.is_lifestyle_follow_up
  out['is_medication_follow_up'] = form.is_medication_follow_up
  if (form.medication_follow_up_stage) out['medication_follow_up_stage'] = form.medication_follow_up_stage
  // Active BP target — SBP/DBP must each be below the given threshold
  if (form.has_active_bp_target) {
    const target: JsonObject = {}
    if (form.target_sbp_upper) target['sbp'] = { upper_exclusive_mmhg: num(form.target_sbp_upper)! }
    if (form.target_dbp_upper) target['dbp'] = { upper_exclusive_mmhg: num(form.target_dbp_upper)! }
    out['active_bp_target'] = target
  }

  return out
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeader({
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

function BpRow({ label, sbpKey, dbpKey, form, onChange, disabled }: BpRowProps) {
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

function Toggle({ label, fieldKey, form, onChange, disabled, note }: ToggleProps) {
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

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

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
      setValidationError('Clinic Measure 1 SBP and DBP are required positive numbers.')
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

    setValidationError(null)
    return formToPayload(form)
  }

  /** Tree 1 (initial diagnosis) has no awareness of follow-up visits — it always
   * requires clinic_2/clinic_3 readings. Follow-up patients must enter at Tree 3,
   * which reads is_lifestyle_follow_up / is_medication_follow_up directly. */
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
          <>
            <div className="ps-sub-label">Initial Clinic Readings</div>
            <BpRow label="Measure 1" sbpKey="clinic_1_sbp" dbpKey="clinic_1_dbp" form={form} onChange={setStr} disabled={isRunning} />
            <BpRow label="Measure 2" sbpKey="clinic_2_sbp" dbpKey="clinic_2_dbp" form={form} onChange={setStr} disabled={isRunning} />
            <BpRow label="Measure 3" sbpKey="clinic_3_sbp" dbpKey="clinic_3_dbp" form={form} onChange={setStr} disabled={isRunning} />

            <div className="ps-sub-label" style={{ marginTop: 8 }}>Follow-Up</div>
            <BpRow label="Pre-Lifestyle" sbpKey="pre_lifestyle_clinic_sbp" dbpKey="pre_lifestyle_clinic_dbp" form={form} onChange={setStr} disabled={isRunning} />

            <div className="ps-sub-label" style={{ marginTop: 8 }}>Out-of-Office / Ambulatory</div>
            <BpRow label="Home" sbpKey="home_sbp" dbpKey="home_dbp" form={form} onChange={setStr} disabled={isRunning} />
            <BpRow label="Daytime" sbpKey="daytime_sbp" dbpKey="daytime_dbp" form={form} onChange={setStr} disabled={isRunning} />
            <BpRow label="Morning" sbpKey="morning_sbp" dbpKey="morning_dbp" form={form} onChange={setStr} disabled={isRunning} />
            <BpRow label="24-Hour" sbpKey="bp_24h_sbp" dbpKey="bp_24h_dbp" form={form} onChange={setStr} disabled={isRunning} />
          </>
        )}

        {/* ========== SECTION 2: Demographics ========== */}
        <SectionHeader label="Demographics & Risk" icon="👤" open={openSections.demographics} onToggle={() => toggleSection('demographics')} />
        {openSections.demographics && (
          <>
            <div className="ps-field-row">
              <div className="ps-field">
                <label className="ps-field-label">Age (years)</label>
                <input
                  className="ps-num-input"
                  type="number" min={1} max={120}
                  placeholder="e.g. 65"
                  value={form.age}
                  onChange={(e) => setStr('age', e.target.value)}
                  disabled={isRunning}
                />
              </div>
              <div className="ps-field">
                <label className="ps-field-label">
                  Risk Factors
                  <span className="ps-field-hint" title="Age >65, Male sex, Smoking, Elevated LDL, Obesity, HR >80, Family history CVD, Premature menopause, Prediabetes, Physical inactivity">ⓘ</span>
                </label>
                <input
                  className="ps-num-input"
                  type="number" min={0} max={10}
                  placeholder="0 – 10"
                  value={form.risk_factor_count}
                  onChange={(e) => setStr('risk_factor_count', e.target.value)}
                  disabled={isRunning}
                />
              </div>
            </div>

            <div className="ps-toggles">
              <Toggle label="Pregnant" fieldKey="is_pregnant" form={form} onChange={setBool} disabled={isRunning} />
            </div>
          </>
        )}

        {/* ========== SECTION 3: Comorbidities ========== */}
        <SectionHeader label="Comorbidities & Clinical Flags" icon={<HeartPulse size={13} />} open={openSections.comorbidities} onToggle={() => toggleSection('comorbidities')} />
        {openSections.comorbidities && (
          <>
            <div className="ps-toggles">
              <Toggle label="Coronary Artery Disease" fieldKey="has_coronary_artery_disease" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Type 2 Diabetes" fieldKey="has_type_2_diabetes" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Diabetes (general)" fieldKey="has_diabetes" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Heart Failure" fieldKey="has_heart_failure" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Chronic Kidney Disease" fieldKey="has_ckd" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="CKD Stage 3+" fieldKey="has_ckd_stage_3_or_higher" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Cardiovascular Disease" fieldKey="has_cardiovascular_disease" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Stroke (history)" fieldKey="has_stroke" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="TIA (history)" fieldKey="has_tia" form={form} onChange={setBool} disabled={isRunning} note="Transient Ischemic Attack" />
              <Toggle label="Frailty Syndrome" fieldKey="has_frailty_syndrome" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Target Organ Damage" fieldKey="has_target_organ_damage" form={form} onChange={setBool} disabled={isRunning} note="Drives the hypertensive-emergency crisis branch" />
            </div>

            {form.has_coronary_artery_disease && (
              <>
                <div className="ps-sub-label" style={{ marginTop: 8 }}>Coronary Artery Disease Detail</div>
                <div className="ps-toggles">
                  <Toggle label="Acute MI / ACS" fieldKey="has_mi_acs" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="CCS Angina" fieldKey="has_ccs_angina" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="CCS Post-Revascularization" fieldKey="has_ccs_revasc" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="CABG (history)" fieldKey="has_cabg" form={form} onChange={setBool} disabled={isRunning} />
                </div>
              </>
            )}

            {form.has_heart_failure && (
              <>
                <div className="ps-sub-label" style={{ marginTop: 8 }}>Heart Failure Detail</div>
                <div className="ps-toggles">
                  <Toggle label="HFrEF (reduced EF)" fieldKey="has_hfref" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="HFmrEF (mildly reduced EF)" fieldKey="has_hfmref" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="HFpEF (preserved EF)" fieldKey="has_hfpef" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Left Ventricular Hypertrophy" fieldKey="has_lvh" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="BP Target Reached" fieldKey="bp_target_reached" form={form} onChange={setBool} disabled={isRunning} />
                </div>
              </>
            )}

            {form.has_ckd && (
              <>
                <div className="ps-sub-label" style={{ marginTop: 8 }}>Chronic Kidney Disease Detail</div>
                <div className="ps-toggles">
                  <Toggle label="Kidney Transplant (history)" fieldKey="has_kidney_transplant" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Prior Creatinine Test on File" fieldKey="has_prior_creatinine_test" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Still Using RAS Inhibitor" fieldKey="still_using_ras_inhibitor" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Creatinine Increased >30%" fieldKey="creatinine_increased_over_30_percent" form={form} onChange={setBool} disabled={isRunning} />
                </div>
              </>
            )}

            {form.has_target_organ_damage && (
              <>
                <div className="ps-sub-label" style={{ marginTop: 8 }}>Hypertensive Emergency Detail</div>
                <div className="ps-toggles">
                  <Toggle label="Acute Ischemic Stroke" fieldKey="has_acute_ischemic_stroke" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Thrombolysis Candidate" fieldKey="is_thrombolysis_candidate" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Acute Coronary Syndrome" fieldKey="has_acute_coronary_syndrome" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Acute Cardiogenic Pulmonary Edema" fieldKey="has_acute_cardiogenic_pulmonary_edema" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Acute Aortic Syndrome" fieldKey="has_acute_aortic_syndrome" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Eclampsia / Severe Preeclampsia / HELLP" fieldKey="has_eclampsia_severe_preeclampsia_or_hellp" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Hypertensive Encephalopathy" fieldKey="has_hypertensive_encephalopathy" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Acute Intracerebral Hemorrhage" fieldKey="has_acute_intracerebral_hemorrhage" form={form} onChange={setBool} disabled={isRunning} />
                </div>
              </>
            )}

            {form.is_pregnant && (
              <>
                <div className="ps-sub-label" style={{ marginTop: 8 }}>Pregnancy Detail</div>
                <div className="ps-toggles">
                  <Toggle label="Pre-Pregnancy Hypertension" fieldKey="has_pre_pregnancy_hypertension" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Hypertension Before Week 20" fieldKey="has_hypertension_before_week_20" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Hypertension After Week 20" fieldKey="has_hypertension_after_week_20" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Prior Gestational Hypertension" fieldKey="has_prior_gestational_hypertension" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="High Preeclampsia Risk" fieldKey="has_high_preeclampsia_risk" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Proteinuria" fieldKey="has_proteinuria" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Autoimmune Disease" fieldKey="has_autoimmune_disease" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Seizure" fieldKey="has_seizure" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Severe Headache" fieldKey="has_severe_headache" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Visual Disturbance" fieldKey="has_visual_disturbance" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Epigastric Pain" fieldKey="has_epigastric_pain" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Hemolysis" fieldKey="has_hemolysis" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Elevated Liver Enzymes" fieldKey="has_elevated_liver_enzymes" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Low Platelets" fieldKey="has_low_platelets" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Pulmonary Edema" fieldKey="has_pulmonary_edema" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Coagulopathy" fieldKey="has_coagulopathy" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Hypertensive Crisis" fieldKey="has_hypertensive_crisis" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Treatment Target Not Achieved" fieldKey="is_treatment_target_not_achieved" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Postpartum" fieldKey="is_postpartum" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Breastfeeding" fieldKey="is_breastfeeding" form={form} onChange={setBool} disabled={isRunning} />
                </div>
                <div className="ps-field-row" style={{ marginTop: 6 }}>
                  <div className="ps-field">
                    <label className="ps-field-label">Proteinuria (24h, mg)</label>
                    <input
                      className="ps-num-input"
                      type="number" min={0}
                      placeholder="e.g. 350"
                      value={form.proteinuria_24h_mg}
                      onChange={(e) => setStr('proteinuria_24h_mg', e.target.value)}
                      disabled={isRunning}
                    />
                  </div>
                  <div className="ps-field">
                    <label className="ps-field-label">ACR (mg/mmol)</label>
                    <input
                      className="ps-num-input"
                      type="number" min={0}
                      placeholder="e.g. 35"
                      value={form.acr_mg_mmol}
                      onChange={(e) => setStr('acr_mg_mmol', e.target.value)}
                      disabled={isRunning}
                    />
                  </div>
                </div>
                <div className="ps-field-row">
                  <div className="ps-field">
                    <label className="ps-field-label">Weeks Persisting Postpartum</label>
                    <input
                      className="ps-num-input"
                      type="number" min={0}
                      placeholder="e.g. 8"
                      value={form.weeks_persisting_postpartum}
                      onChange={(e) => setStr('weeks_persisting_postpartum', e.target.value)}
                      disabled={isRunning}
                    />
                  </div>
                  <div className="ps-field">
                    <label className="ps-field-label">Weeks Resolved Postpartum</label>
                    <input
                      className="ps-num-input"
                      type="number" min={0}
                      placeholder="e.g. 2"
                      value={form.weeks_resolved_postpartum}
                      onChange={(e) => setStr('weeks_resolved_postpartum', e.target.value)}
                      disabled={isRunning}
                    />
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* ========== SECTION 4: Care Setting ========== */}
        <SectionHeader label="Care Setting & Follow-Up" icon="⚙️" open={openSections.care} onToggle={() => toggleSection('care')} />
        {openSections.care && (
          <>
            {/* Active BP Target — kept up top since it drives the follow-up comparison below */}
            <div className="ps-toggles">
              <Toggle label="Has Active BP Target" fieldKey="has_active_bp_target" form={form} onChange={setBool} disabled={isRunning} note="Patient already on therapy" />
            </div>

            {form.has_active_bp_target && (
              <div className="ps-bp-target-box">
                <div className="ps-field-hint" style={{ display: 'block', marginBottom: 6 }}>
                  Target is reached when SBP is below the SBP number AND DBP is below the DBP number.
                </div>
                <div className="ps-field-row">
                  <div className="ps-field">
                    <label className="ps-field-label">Age (years)</label>
                    <input
                      className="ps-num-input"
                      type="number" min={1} max={120}
                      placeholder="e.g. 65"
                      value={form.age}
                      onChange={(e) => setStr('age', e.target.value)}
                      disabled={isRunning}
                    />
                  </div>
                  <div className="ps-field">
                    <label className="ps-field-label">
                      Risk Factors
                      <span className="ps-field-hint" title="Age >65, Male sex, Smoking, Elevated LDL, Obesity, HR >80, Family history CVD, Premature menopause, Prediabetes, Physical inactivity">ⓘ</span>
                    </label>
                    <input
                      className="ps-num-input"
                      type="number" min={0} max={10}
                      placeholder="0 – 10"
                      value={form.risk_factor_count}
                      onChange={(e) => setStr('risk_factor_count', e.target.value)}
                      disabled={isRunning}
                    />
                  </div>
                </div>
                <div className="ps-toggles">
                  <Toggle label="Pregnant" fieldKey="is_pregnant" form={form} onChange={setBool} disabled={isRunning} />
                </div>
              </div>
            )}

            <div className="ps-field" style={{ marginTop: 8 }}>
              <label className="ps-field-label">Facility Capability</label>
              <div className="ps-radio-group">
                {[
                  { value: 'FULL_RESOURCES', label: 'Full Resources' },
                  { value: 'LIMITED_RESOURCES', label: 'Limited Resources' },
                ].map(({ value, label }) => (
                  <label key={value} className="ps-radio-label">
                    <input
                      type="radio"
                      name="facility_capability"
                      value={value}
                      checked={form.facility_capability === value}
                      onChange={() => setStr('facility_capability', value)}
                      disabled={isRunning}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>

            <div className="ps-toggles" style={{ marginTop: 8 }}>
              <Toggle label="Lifestyle Follow-Up Visit" fieldKey="is_lifestyle_follow_up" form={form} onChange={setBool} disabled={isRunning} />
              <Toggle label="Medication Follow-Up Visit" fieldKey="is_medication_follow_up" form={form} onChange={setBool} disabled={isRunning} />
            </div>

            {form.is_medication_follow_up && (
              <div className="ps-field" style={{ marginTop: 8 }}>
                <label className="ps-field-label">Medication Follow-Up Stage</label>
                <div className="ps-radio-group">
                  {[
                    { value: 'INITIAL_REGIMEN', label: 'Initial Regimen' },
                    { value: 'ESCALATED_REGIMEN', label: 'Escalated Regimen' },
                  ].map(({ value, label }) => (
                    <label key={value} className="ps-radio-label">
                      <input
                        type="radio"
                        name="medication_follow_up_stage"
                        value={value}
                        checked={form.medication_follow_up_stage === value}
                        onChange={() => setStr('medication_follow_up_stage', value)}
                        disabled={isRunning}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            )}

            {form.is_medication_follow_up && form.medication_follow_up_stage === 'ESCALATED_REGIMEN' && form.facility_capability === 'LIMITED_RESOURCES' && (
              <>
                <div className="ps-sub-label" style={{ marginTop: 8 }}>Resistant Hypertension Detail (Limited Resources)</div>
                <div className="ps-toggles">
                  <Toggle label="Tolerates MRA" fieldKey="tolerates_mra" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="Tolerates Spironolactone" fieldKey="tolerates_spironolactone" form={form} onChange={setBool} disabled={isRunning} />
                  <Toggle label="BP Target Reached" fieldKey="bp_target_reached" form={form} onChange={setBool} disabled={isRunning} />
                </div>
              </>
            )}
          </>
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
