import type { JsonObject } from '../../api/types'
import type { PatientFormData } from './types'

/** Convert string to number or omit if empty */
function num(v: string): number | undefined {
  const n = parseFloat(v)
  return isNaN(n) ? undefined : n
}

export function formToPayload(form: PatientFormData): JsonObject {
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
