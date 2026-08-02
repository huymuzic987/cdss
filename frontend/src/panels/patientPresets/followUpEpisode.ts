import type { JsonObject } from '../../api/types'
import { flatToBundle } from '../mockPatientForm/fhirBundle'

export const REVIEW_PATIENT_ID = 'medication-follow-up-review-001'

export function medicationFollowUpBundle(values: JsonObject) {
  return flatToBundle({
    is_medication_follow_up: true,
    facility_capability: 'FULL_RESOURCES',
    medication_follow_up_stage: 'INITIAL_REGIMEN',
    active_bp_target_sbp_upper: 130,
    active_bp_target_dbp_upper: 80,
    minimum_regimen_days: 28,
    current_regimen_drug_count: 2,
    current_regimen_drug_classes: 'A+D',
    adherence_adequate: true,
    dose_adequate: true,
    age: 48,
    risk_factor_count: 0,
    ...values,
  }, REVIEW_PATIENT_ID)
}
