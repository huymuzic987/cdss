import type { PatientFormData } from './MockPatientSidebar'

export interface PatientPreset {
  id: string
  label: string
  category: string
  description: string
  data: Partial<PatientFormData>
}

const DIAGNOSIS = 'Diagnosis Routes'
const DEMOGRAPHIC = 'Demographic & Comorbidity Diversity'
const FOLLOW_UP = 'Follow-Up Visits'

const MEDICATION_TARGET: Pick<
  PatientFormData,
  'has_active_bp_target' | 'target_sbp_upper' | 'target_dbp_upper'
> = {
  has_active_bp_target: true,
  target_sbp_upper: '130',
  target_dbp_upper: '80',
}

export const PATIENT_PRESETS: PatientPreset[] = [
  // ---- Diagnosis Routes ----
  {
    id: 'normal-bp',
    label: 'Healthy Adult — Normal BP',
    category: DIAGNOSIS,
    description: 'Textbook normal readings, no risk factors.',
    data: {
      clinic_1_sbp: '120', clinic_1_dbp: '80',
      clinic_2_sbp: '120', clinic_2_dbp: '80',
      clinic_3_sbp: '120', clinic_3_dbp: '80',
      age: '42', risk_factor_count: '0',
    },
  },
  {
    id: 'stage1-htn',
    label: 'Stage 1 Hypertension — Newly Diagnosed',
    category: DIAGNOSIS,
    description: 'Borderline elevated clinic readings; typical new-diagnosis presentation.',
    data: {
      clinic_1_sbp: '135', clinic_1_dbp: '85',
      clinic_2_sbp: '138', clinic_2_dbp: '86',
      clinic_3_sbp: '136', clinic_3_dbp: '84',
      age: '50', risk_factor_count: '2',
    },
  },
  {
    id: 'stage2-htn',
    label: 'Stage 2 Hypertension',
    category: DIAGNOSIS,
    description: 'Clearly elevated clinic readings across all three visits.',
    data: {
      clinic_1_sbp: '150', clinic_1_dbp: '95',
      clinic_2_sbp: '148', clinic_2_dbp: '93',
      clinic_3_sbp: '152', clinic_3_dbp: '96',
      age: '55', risk_factor_count: '3',
    },
  },
  {
    id: 'hypertensive-emergency',
    label: 'Hypertensive Emergency',
    category: DIAGNOSIS,
    description: 'SBP ≥180 crisis threshold; routes to the (currently unseeded) emergency tree.',
    data: {
      clinic_1_sbp: '182', clinic_1_dbp: '80',
      age: '58', risk_factor_count: '2',
    },
  },
  {
    id: 'ambulatory-confirmation',
    label: 'Borderline BP — Home/Ambulatory Confirmation',
    category: DIAGNOSIS,
    description: 'Ambiguous clinic readings plus a full set of out-of-office measurements.',
    data: {
      clinic_1_sbp: '138', clinic_1_dbp: '86',
      clinic_2_sbp: '136', clinic_2_dbp: '85',
      clinic_3_sbp: '139', clinic_3_dbp: '87',
      home_sbp: '135', home_dbp: '85',
      daytime_sbp: '138', daytime_dbp: '87',
      morning_sbp: '140', morning_dbp: '88',
      bp_24h_sbp: '132', bp_24h_dbp: '84',
      age: '50', risk_factor_count: '2',
    },
  },

  // ---- Demographic & Comorbidity Diversity ----
  {
    id: 'elderly-ckd',
    label: 'Elderly with CKD Stage 3+ & Organ Damage',
    category: DEMOGRAPHIC,
    description: '78-year-old with chronic kidney disease and target organ damage.',
    data: {
      clinic_1_sbp: '155', clinic_1_dbp: '92',
      clinic_2_sbp: '152', clinic_2_dbp: '90',
      clinic_3_sbp: '156', clinic_3_dbp: '93',
      age: '78', risk_factor_count: '4',
      has_ckd: true, has_ckd_stage_3_or_higher: true, has_target_organ_damage: true,
    },
  },
  {
    id: 'diabetic-cad',
    label: 'Diabetic with Coronary Artery Disease',
    category: DEMOGRAPHIC,
    description: '62-year-old with type 2 diabetes and established CAD.',
    data: {
      clinic_1_sbp: '148', clinic_1_dbp: '94',
      clinic_2_sbp: '146', clinic_2_dbp: '92',
      clinic_3_sbp: '150', clinic_3_dbp: '95',
      age: '62', risk_factor_count: '5',
      has_type_2_diabetes: true, has_diabetes: true,
      has_coronary_artery_disease: true, has_cardiovascular_disease: true,
    },
  },
  {
    id: 'post-stroke',
    label: 'Post-Stroke / TIA History',
    category: DEMOGRAPHIC,
    description: '70-year-old with prior stroke and TIA.',
    data: {
      clinic_1_sbp: '150', clinic_1_dbp: '92',
      clinic_2_sbp: '148', clinic_2_dbp: '90',
      clinic_3_sbp: '151', clinic_3_dbp: '93',
      age: '70', risk_factor_count: '4',
      has_stroke: true, has_tia: true, has_cardiovascular_disease: true,
    },
  },
  {
    id: 'frail-elderly',
    label: 'Frail Older Adult with Heart Failure',
    category: DEMOGRAPHIC,
    description: '85-year-old, frailty syndrome and heart failure.',
    data: {
      clinic_1_sbp: '158', clinic_1_dbp: '96',
      clinic_2_sbp: '156', clinic_2_dbp: '94',
      clinic_3_sbp: '159', clinic_3_dbp: '97',
      age: '85', risk_factor_count: '2',
      has_frailty_syndrome: true, has_heart_failure: true,
    },
  },
  {
    id: 'high-risk-young',
    label: 'Young Adult, High Risk-Factor Load',
    category: DEMOGRAPHIC,
    description: '45-year-old, no diagnosed comorbidities yet but 8 risk factors.',
    data: {
      clinic_1_sbp: '138', clinic_1_dbp: '88',
      clinic_2_sbp: '140', clinic_2_dbp: '89',
      clinic_3_sbp: '137', clinic_3_dbp: '87',
      age: '45', risk_factor_count: '8',
    },
  },

  // ---- Follow-Up Visits ----
  {
    id: 'lifestyle-followup',
    label: 'Lifestyle Follow-Up — BP Improved',
    category: FOLLOW_UP,
    description: 'Meets the stored 10/5 mmHg reduction rule after lifestyle changes.',
    data: {
      clinic_1_sbp: '140', clinic_1_dbp: '90',
      is_lifestyle_follow_up: true,
      pre_lifestyle_clinic_sbp: '150', pre_lifestyle_clinic_dbp: '95',
      current_clinic_sbp: '140', current_clinic_dbp: '90',
      age: '55', risk_factor_count: '2',
    },
  },
  {
    id: 'med-followup-reached-full',
    label: 'Medication Follow-Up — Target Reached (Full Resources)',
    category: FOLLOW_UP,
    description: 'On initial regimen, current BP within active target, full-resource facility.',
    data: {
      clinic_1_sbp: '129', clinic_1_dbp: '79',
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
      clinic_1_sbp: '129', clinic_1_dbp: '79',
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
      clinic_1_sbp: '130', clinic_1_dbp: '80',
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
      clinic_1_sbp: '130', clinic_1_dbp: '80',
      is_medication_follow_up: true,
      facility_capability: 'FULL_RESOURCES',
      medication_follow_up_stage: 'ESCALATED_REGIMEN',
      ...MEDICATION_TARGET,
      current_clinic_sbp: '130', current_clinic_dbp: '80',
      age: '65', risk_factor_count: '3',
    },
  },
]
