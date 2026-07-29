import { DEMOGRAPHIC, type PatientPresetDefinition } from './shared'

export const demographicPresets: PatientPresetDefinition[] = [
  {
    id: 'elderly-ckd',
    label: 'Elderly with CKD Stage 3+ & Organ Damage',
    category: DEMOGRAPHIC,
    description: '78-year-old with chronic kidney disease and target organ damage.',
    data: {
      current_clinic_sbp: '155', current_clinic_dbp: '92',
      age: '78', risk_factor_count: '4',
      has_ckd: true, has_ckd_stage_3_or_higher: true, has_target_organ_damage: true,
    },
  },
  {
    id: 'diabetic-cad',
    label: 'Diabetic with Coronary Artery Disease',
    category: DEMOGRAPHIC,
    description: '62-year-old with type 2 diabetes and established CAD. CAD is checked before type-2-diabetes in Tree 3’s modifier order, so this routes into the coronary-artery-disease tree (CCS angina action); the diabetes flag is recorded but that tree never runs in this same traversal. Routes to Tree 4 (Essential Treatment Strategy) or Tree 5 (Optimal Treatment Strategy).',
    data: {
      current_clinic_sbp: '150', current_clinic_dbp: '95',
      age: '62', risk_factor_count: '5',
      has_type_2_diabetes: true, has_diabetes: true,
      has_coronary_artery_disease: true, has_cardiovascular_disease: true,
      has_ccs_angina: true,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'post-stroke',
    label: 'Post-Stroke / TIA History',
    category: DEMOGRAPHIC,
    description: '70-year-old with prior stroke and TIA.',
    data: {
      current_clinic_sbp: '150', current_clinic_dbp: '92',
      age: '70', risk_factor_count: '4',
      has_stroke: true, has_tia: true, has_cardiovascular_disease: true,
    },
  },
  {
    id: 'frail-elderly',
    label: 'Frail Older Adult with Heart Failure',
    category: DEMOGRAPHIC,
    description: '85-year-old, frailty syndrome and heart failure. Heart failure is checked before the (unseeded) older-adult modifier at Tree 3, so this now routes into the heart-failure tree — HFrEF, target not yet reached — instead of the older-adult dead link.',
    data: {
      current_clinic_sbp: '159', current_clinic_dbp: '97',
      age: '85', risk_factor_count: '2',
      has_frailty_syndrome: true, has_heart_failure: true,
      has_hfref: true,
      bp_target_reached: false,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'high-risk-young',
    label: 'Young Adult, High Risk-Factor Load',
    category: DEMOGRAPHIC,
    description: '45-year-old, no diagnosed comorbidities yet but 8 risk factors.',
    data: {
      current_clinic_sbp: '138', current_clinic_dbp: '88',
      age: '45', risk_factor_count: '8',
      facility_capability: 'FULL_RESOURCES',
    },
  },

  // ---- Follow-Up Visits ----
]
