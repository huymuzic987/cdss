import type { JsonObject } from '../../api/types'
import { formToPayload } from './payload'
import type { PatientFormData } from './types'

export type PatientFormValidation =
  | { payload: JsonObject; error: null }
  | { payload: null; error: string }

function invalid(error: string): PatientFormValidation {
  return { payload: null, error }
}

export function validatePatientForm(form: PatientFormData): PatientFormValidation {
  const clinicSbp = Number.parseFloat(form.current_clinic_sbp)
  const clinicDbp = Number.parseFloat(form.current_clinic_dbp)
  if (!form.current_clinic_sbp || !form.current_clinic_dbp
    || Number.isNaN(clinicSbp) || Number.isNaN(clinicDbp)
    || clinicSbp <= 0 || clinicDbp <= 0) {
    return invalid('Clinic SBP and DBP are required positive numbers.')
  }

  const age = Number.parseFloat(form.age)
  if (!form.age || Number.isNaN(age) || age <= 0) {
    return invalid('Age is required and must be a valid positive number.')
  }

  const riskFactorCount = Number.parseFloat(form.risk_factor_count)
  if (!form.risk_factor_count || Number.isNaN(riskFactorCount) || riskFactorCount < 0) {
    return invalid('Risk Factor Count is required and must be 0 or higher.')
  }

  const hasPreviousSbp = form.previous_sbp !== ''
  const hasPreviousDbp = form.previous_dbp !== ''
  if (hasPreviousSbp !== hasPreviousDbp) {
    return invalid('Enter both previous-visit SBP and DBP, or leave both empty.')
  }
  if (hasPreviousSbp) {
    const previousSbp = Number.parseFloat(form.previous_sbp)
    const previousDbp = Number.parseFloat(form.previous_dbp)
    if (Number.isNaN(previousSbp) || Number.isNaN(previousDbp)
      || previousSbp <= 0 || previousDbp <= 0) {
      return invalid('Previous-visit SBP and DBP must be positive numbers.')
    }
  }

  if (form.medication_follow_up_stage !== '') {
    const targetSbp = Number.parseFloat(form.target_sbp_upper)
    const targetDbp = Number.parseFloat(form.target_dbp_upper)
    if (!form.target_sbp_upper || !form.target_dbp_upper
      || Number.isNaN(targetSbp) || Number.isNaN(targetDbp)
      || targetSbp <= 0 || targetDbp <= 0) {
      return invalid('A known medication follow-up stage requires an Active BP Target (SBP and DBP).')
    }
  }

  return { payload: formToPayload(form), error: null }
}
