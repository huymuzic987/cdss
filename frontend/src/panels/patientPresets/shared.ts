import type { PatientFormData } from '../mockPatientForm/types'
import type { JsonObject } from '../../api/types'

export interface PatientPreset {
  id: string
  label: string
  category: string
  description: string
  bundle: JsonObject
}

export interface PatientPresetFormDefinition extends Omit<PatientPreset, 'bundle'> {
  data: Partial<PatientFormData>
}

export interface PatientPresetBundleDefinition extends Omit<PatientPreset, 'bundle'> {
  bundle: JsonObject
}

export type PatientPresetDefinition =
  | PatientPresetFormDefinition
  | PatientPresetBundleDefinition

export const DIAGNOSIS = 'Diagnosis Routes'
export const DEMOGRAPHIC = 'Demographic & Comorbidity Diversity'
export const FOLLOW_UP = 'Follow-Up Visits'
export const MODIFIER_TREES = 'Modifier & Complication Trees'
export const PREGNANCY = 'Pregnancy & Postpartum'
export const PREGNANCY_FOLLOW_UP = 'Pregnancy Follow-Up Sequence'

export const MEDICATION_TARGET: Pick<
  PatientFormData,
  'target_sbp_upper' | 'target_dbp_upper'
> = {
  target_sbp_upper: '130',
  target_dbp_upper: '80',
}
