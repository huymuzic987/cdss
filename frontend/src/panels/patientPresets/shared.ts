import type { PatientFormData } from '../mockPatientForm/types'
import type { JsonObject } from '../../api/types'

export interface PatientPreset {
  id: string
  label: string
  category: string
  description: string
  bundle: JsonObject
}

export interface PatientPresetDefinition extends Omit<PatientPreset, 'bundle'> {
  data: Partial<PatientFormData>
}

export const DIAGNOSIS = 'Diagnosis Routes'
export const DEMOGRAPHIC = 'Demographic & Comorbidity Diversity'
export const FOLLOW_UP = 'Follow-Up Visits'
export const MODIFIER_TREES = 'Modifier & Complication Trees'
export const PREGNANCY = 'Pregnancy & Postpartum'

export const MEDICATION_TARGET: Pick<
  PatientFormData,
  'target_sbp_upper' | 'target_dbp_upper' | 'previous_sbp' | 'previous_dbp'
> = {
  target_sbp_upper: '130',
  target_dbp_upper: '80',
  previous_sbp: '150',
  previous_dbp: '95',
}
