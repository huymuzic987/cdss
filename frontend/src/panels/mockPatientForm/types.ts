// ---------------------------------------------------------------------------
// Form state definition
// ---------------------------------------------------------------------------

export interface PatientFormData {
  // BP — today's visit reading (initial diagnosis or follow-up alike)
  current_clinic_sbp: string
  current_clinic_dbp: string
  previous_sbp: string
  previous_dbp: string
  previous_target_sbp: string
  previous_target_dbp: string
  // BP — home (pregnancy gestational-hypertension classification)
  home_sbp: string
  home_dbp: string
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
  has_tma_or_acute_kidney_injury: boolean
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
  current_regimen_drug_classes: string
  // Active BP target (required for medication follow-up)
  target_sbp_upper: string
  target_dbp_upper: string
}

export const DEFAULT_FORM: PatientFormData = {
  current_clinic_sbp: '', current_clinic_dbp: '',
  previous_sbp: '', previous_dbp: '',
  previous_target_sbp: '', previous_target_dbp: '',
  home_sbp: '', home_dbp: '',
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
  has_tma_or_acute_kidney_injury: false,
  is_treatment_target_not_achieved: false,
  is_postpartum: false,
  is_breastfeeding: false,
  weeks_persisting_postpartum: '',
  weeks_resolved_postpartum: '',
  facility_capability: '',
  is_lifestyle_follow_up: false,
  is_medication_follow_up: false,
  medication_follow_up_stage: '',
  current_regimen_drug_classes: '',
  target_sbp_upper: '',
  target_dbp_upper: '',
}

export interface FormSectionProps {
  form: PatientFormData
  setStr: (key: keyof PatientFormData, value: string) => void
  setBool: (key: keyof PatientFormData, value: boolean) => void
  disabled?: boolean
}
