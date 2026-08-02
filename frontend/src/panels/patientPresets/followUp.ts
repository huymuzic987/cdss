import { FOLLOW_UP, MEDICATION_TARGET, type PatientPresetDefinition } from './shared'
import { flatToBundle } from '../mockPatientForm/fhirBundle'
import { formToPayload } from '../mockPatientForm/payload'
import { DEFAULT_FORM } from '../mockPatientForm/types'

const REVIEW_PATIENT_ID = 'medication-follow-up-review-001'

function medicationFollowUpBundle(values: Record<string, string | number | boolean>) {
  return flatToBundle({
    is_medication_follow_up: true,
    facility_capability: 'FULL_RESOURCES',
    medication_follow_up_stage: 'INITIAL_REGIMEN',
    active_bp_target_sbp_upper: 130,
    active_bp_target_dbp_upper: 80,
    minimum_regimen_days: 28,
    current_regimen_drug_count: 1,
    adherence_adequate: true,
    dose_adequate: true,
    age: 48,
    risk_factor_count: 0,
    ...values,
  }, REVIEW_PATIENT_ID)
}

export const followUpPresets: PatientPresetDefinition[] = [
  {
    id: 'med-review-episode-initial-one-drug',
    label: 'Medication Episode — Initial: One Drug',
    category: FOLLOW_UP,
    description: 'Initial visit for review patient medication-follow-up-review-001; intended starting state is one-drug treatment.',
    bundle: formToPayload({
      ...DEFAULT_FORM,
      current_clinic_sbp: '145',
      current_clinic_dbp: '92',
      age: '48',
      risk_factor_count: '0',
      facility_capability: 'FULL_RESOURCES',
    }, REVIEW_PATIENT_ID),
  },
  {
    id: 'med-review-episode-follow-up-1-replace',
    label: 'Medication Episode — Follow-Up 1: Replace Drug',
    category: FOLLOW_UP,
    description: 'BP is uncontrolled, but one drug is unusable. Stops at the initial-regimen checkpoint and replaces only that drug.',
    bundle: medicationFollowUpBundle({
      current_clinic_sbp: 145,
      current_clinic_dbp: 90,
      assessment_date: '2026-01-29',
      regimen_effective_date: '2026-01-01',
      drug_replacement_required: true,
    }),
  },
  {
    id: 'med-review-episode-follow-up-2-escalate',
    label: 'Medication Episode — Follow-Up 2: Escalate to Two Drugs',
    category: FOLLOW_UP,
    description: 'The replacement drug has had a complete 28-day trial; BP remains above target, so normal traversal reaches the existing escalation action.',
    bundle: medicationFollowUpBundle({
      current_clinic_sbp: 142,
      current_clinic_dbp: 88,
      assessment_date: '2026-02-26',
      regimen_effective_date: '2026-01-29',
    }),
  },
  {
    id: 'med-review-episode-follow-up-3-early',
    label: 'Medication Episode — Follow-Up 3: Early Arrival',
    category: FOLLOW_UP,
    description: 'Patient is now on the two-drug/escalated stage but returns before 2026-03-26 with no drug change; traversal stops and continues the regimen.',
    bundle: medicationFollowUpBundle({
      medication_follow_up_stage: 'ESCALATED_REGIMEN',
      current_regimen_drug_count: 2,
      current_clinic_sbp: 138,
      current_clinic_dbp: 84,
      assessment_date: '2026-03-10',
      regimen_effective_date: '2026-02-26',
    }),
  },
  {
    id: 'med-review-episode-follow-up-4-controlled',
    label: 'Medication Episode — Follow-Up 4: Target Reached',
    category: FOLLOW_UP,
    description: 'On the scheduled reassessment date, BP is below target and normal traversal follows the escalated-regimen target-reached branch.',
    bundle: medicationFollowUpBundle({
      medication_follow_up_stage: 'ESCALATED_REGIMEN',
      current_regimen_drug_count: 2,
      current_clinic_sbp: 126,
      current_clinic_dbp: 76,
      assessment_date: '2026-03-26',
      regimen_effective_date: '2026-02-26',
    }),
  },
  {
    id: 'lifestyle-followup',
    label: 'Lifestyle Follow-Up — BP Improved',
    category: FOLLOW_UP,
    description: 'Meets the stored 15/10 mmHg reduction rule after lifestyle changes.',
    data: {
      is_lifestyle_follow_up: true,
      previous_sbp: '130', previous_dbp: '85',
      previous_target_sbp: '140', previous_target_dbp: '90',
      current_clinic_sbp: '115', current_clinic_dbp: '75',
      age: '55', risk_factor_count: '2',
    },
  },
  {
    id: 'med-followup-reached-full',
    label: 'Medication Follow-Up — Target Reached (Full Resources)',
    category: FOLLOW_UP,
    description: 'On initial regimen, current BP within active target, full-resource facility.',
    data: {
      is_medication_follow_up: true,
      facility_capability: 'FULL_RESOURCES',
      medication_follow_up_stage: 'INITIAL_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '129', current_clinic_dbp: '79',
      age: '60', risk_factor_count: '2',
    },
  },
  {
    id: 'med-followup-reached-limited',
    label: 'Medication Follow-Up — Target Reached (Limited Resources)',
    category: FOLLOW_UP,
    description: 'Same as above but a limited-resource facility — different terminal action wording.',
    data: {
      is_medication_follow_up: true,
      facility_capability: 'LIMITED_RESOURCES',
      medication_follow_up_stage: 'INITIAL_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '129', current_clinic_dbp: '79',
      age: '60', risk_factor_count: '2',
    },
  },
  {
    id: 'med-followup-not-reached-initial',
    label: 'Medication Follow-Up — Initial Regimen, Target Not Reached',
    category: FOLLOW_UP,
    description: 'Initial regimen insufficient — routes toward drug-combination escalation.',
    data: {
      is_medication_follow_up: true,
      facility_capability: 'FULL_RESOURCES',
      medication_follow_up_stage: 'INITIAL_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '130', current_clinic_dbp: '80',
      age: '63', risk_factor_count: '3',
    },
  },
  {
    id: 'med-followup-resistant',
    label: 'Medication Follow-Up — Resistant Hypertension (Escalated)',
    category: FOLLOW_UP,
    description: 'Escalated regimen, target not reached — resistant hypertension path.',
    data: {
      is_medication_follow_up: true,
      facility_capability: 'FULL_RESOURCES',
      medication_follow_up_stage: 'ESCALATED_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '130', current_clinic_dbp: '80',
      age: '65', risk_factor_count: '3',
    },
  },
  {
    id: 'med-followup-resistant-limited',
    label: 'Medication Follow-Up — Resistant Hypertension (Limited Resources)',
    category: FOLLOW_UP,
    description: 'Escalated regimen, target not reached, limited-resource facility — reaches resistant-hypertension via the known-stage /evaluate/follow-up endpoint, but currently halts at the first action (CHECK_MRA): the walker only continues past an ACTION node for a small allowlist of trees, which resistant-hypertension is not part of. Fixing that traversal-engine gap is a separate, not-yet-scheduled change.',
    data: {
      is_medication_follow_up: true,
      facility_capability: 'LIMITED_RESOURCES',
      medication_follow_up_stage: 'ESCALATED_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '135', current_clinic_dbp: '85',
      tolerates_mra: true,
      bp_target_reached: false,
      age: '65', risk_factor_count: '3',
    },
  },
  {
    id: 'med-followup-resistant-spironolactone',
    label: 'Medication Follow-Up — Resistant HTN, MRA Not Tolerated, Spironolactone Added',
    category: FOLLOW_UP,
    description: 'Escalated regimen, target not yet reached at the treatment-strategy level (so it enters resistant-hypertension), MRA not tolerated but spironolactone is — same known walker limitation as the preset above means this currently halts at CHECK_MRA rather than reaching the spironolactone/maintain outcome the tree logic describes.',
    data: {
      is_medication_follow_up: true,
      facility_capability: 'LIMITED_RESOURCES',
      medication_follow_up_stage: 'ESCALATED_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '135', current_clinic_dbp: '85',
      tolerates_mra: false,
      tolerates_spironolactone: true,
      bp_target_reached: true,
      age: '65', risk_factor_count: '3',
    },
  },
  {
    id: 'med-followup-resistant-alternatives',
    label: 'Medication Follow-Up — Resistant HTN, Neither MRA Nor Spironolactone Tolerated',
    category: FOLLOW_UP,
    description: 'Escalated regimen, patient tolerates neither MRA nor spironolactone — same known walker limitation as the two presets above means this currently halts at CHECK_MRA rather than reaching the therapeutic-alternatives/referral outcome the tree logic describes.',
    data: {
      is_medication_follow_up: true,
      facility_capability: 'LIMITED_RESOURCES',
      medication_follow_up_stage: 'ESCALATED_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '135', current_clinic_dbp: '85',
      tolerates_mra: false,
      tolerates_spironolactone: false,
      bp_target_reached: false,
      age: '65', risk_factor_count: '3',
    },
  },

  // ---- Modifier & Complication Trees ----
]
