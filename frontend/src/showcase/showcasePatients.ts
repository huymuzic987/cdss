import type { JsonObject } from '../api/types'
import { bundleToForm } from '../panels/mockPatientForm/payload'
import type { PatientFormData } from '../panels/mockPatientForm/types'
import { PATIENT_PRESETS } from '../panels/patientPresets'

export type ShowcaseEvaluationMode = 'initial' | 'follow-up'
export type ShowcasePriority = 'routine' | 'review' | 'priority'

export interface ShowcasePatient {
  id: string
  name: string
  initials: string
  mrn: string
  sex: string
  visitType: string
  status: string
  priority: ShowcasePriority
  note: string
  presetId: string
  evaluationMode: ShowcaseEvaluationMode
  bundle: JsonObject
  form: PatientFormData
}

function initials(label: string): string {
  const words = label.replace(/[^a-zA-Z0-9 ]/g, ' ').split(/\s+/).filter(Boolean)
  return words.slice(0, 2).map((word) => word[0]?.toUpperCase()).join('') || 'PT'
}

function presentation(form: PatientFormData): Pick<ShowcasePatient, 'priority' | 'status'> {
  const systolic = Number(form.current_clinic_sbp)
  const diastolic = Number(form.current_clinic_dbp)
  if (systolic >= 180 || diastolic >= 120) return { priority: 'priority', status: 'Crisis BP' }
  if (systolic >= 140 || diastolic >= 90) return { priority: 'priority', status: 'High BP' }
  if (systolic >= 130 || diastolic >= 80) return { priority: 'review', status: 'Review BP' }
  if (form.medication_follow_up_stage) return { priority: 'routine', status: 'Follow-up' }
  return { priority: 'routine', status: 'Routine' }
}

export const SHOWCASE_PATIENTS: ShowcasePatient[] = PATIENT_PRESETS.map((preset) => {
  const form = bundleToForm(preset.bundle)
  return {
    id: preset.id,
    name: preset.label,
    initials: initials(preset.label),
    mrn: `Preset · ${preset.id}`,
    sex: 'Patient',
    visitType: preset.category,
    status: presentation(form).status,
    priority: presentation(form).priority,
    note: preset.description,
    presetId: preset.id,
    evaluationMode: form.medication_follow_up_stage ? 'follow-up' : 'initial',
    bundle: preset.bundle,
    form,
  }
})

const flagLabels: [keyof PatientFormData, string][] = [
  ['has_ckd', 'Chronic kidney disease'], ['has_ckd_stage_3_or_higher', 'CKD stage 3 or higher'],
  ['has_target_organ_damage', 'Target-organ damage'], ['has_type_2_diabetes', 'Type 2 diabetes'],
  ['has_coronary_artery_disease', 'Coronary artery disease'], ['has_cardiovascular_disease', 'Cardiovascular disease'],
  ['has_heart_failure', 'Heart failure'], ['has_stroke', 'Previous stroke'], ['has_tia', 'Previous TIA'],
  ['has_frailty_syndrome', 'Frailty syndrome'],
]

export function clinicalFlags(form: PatientFormData): string[] {
  const flags = flagLabels.filter(([key]) => form[key] === true).map(([, label]) => label)
  if (form.is_pregnant) flags.push('Pregnant')
  return flags
}

export function formatBloodPressure(sbp: string, dbp: string): string {
  return sbp && dbp ? `${sbp}/${dbp}` : 'Not recorded'
}

