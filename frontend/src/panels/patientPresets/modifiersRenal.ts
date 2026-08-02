import { MODIFIER_TREES, type PatientPresetDefinition } from './shared'

export const renalModifierPresets: PatientPresetDefinition[] = [
  {
    id: 'heart-failure-hfpef',
    label: 'Heart Failure — Preserved EF (HFpEF)',
    category: MODIFIER_TREES,
    description: '65-year-old with HFpEF, BP target not yet reached — combines diuretic/SGLT2i/aldosterone antagonist then ARNI/CTTA, the third of the four EF-category branches.',
    data: {
      current_clinic_sbp: '159', current_clinic_dbp: '97',
      age: '65', risk_factor_count: '2',
      has_heart_failure: true,
      has_hfpef: true,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'heart-failure-lvh',
    label: 'Heart Failure Tree — LVH (No Reduced EF)',
    category: MODIFIER_TREES,
    description: '65-year-old with left ventricular hypertrophy but no HFrEF/HFmrEF/HFpEF flag, BP target not yet reached — the fourth and last EF-evaluation branch, adds an A+C or A+D combination.',
    data: {
      current_clinic_sbp: '159', current_clinic_dbp: '97',
      age: '65', risk_factor_count: '2',
      has_heart_failure: true,
      has_lvh: true,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'heart-failure-target-reached',
    label: 'Heart Failure — HFrEF, BP Target Reached (Maintain)',
    category: MODIFIER_TREES,
    description: '65-year-old with HFrEF whose BP is above the entry threshold but already at the personal target — after EF evaluation, maintains the current regimen instead of adding a CCB/adjusting dosage.',
    data: {
      current_clinic_sbp: '125', current_clinic_dbp: '75',
      age: '65', risk_factor_count: '2',
      has_heart_failure: true,
      has_hfref: true,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'ckd-kidney-transplant',
    label: 'Chronic Kidney Disease — Post-Transplant',
    category: MODIFIER_TREES,
    description: '50-year-old with CKD and a kidney transplant — uses the stricter post-transplant BP target (130/80) and a narrower combination list, then maintains the current regimen.',
    data: {
      current_clinic_sbp: '135', current_clinic_dbp: '92',
      age: '50', risk_factor_count: '2',
      has_ckd: true,
      has_kidney_transplant: true,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'ckd-ras-inhibitor-stopped',
    label: 'Chronic Kidney Disease — Prior Test, RAS Inhibitor Already Stopped',
    category: MODIFIER_TREES,
    description: '50-year-old with CKD, has a prior creatinine test on file, and is no longer on a RAS inhibitor — maintains the current regimen without re-testing creatinine.',
    data: {
      current_clinic_sbp: '135', current_clinic_dbp: '92',
      age: '50', risk_factor_count: '2',
      has_ckd: true,
      has_prior_creatinine_test: true,
      still_using_ras_inhibitor: false,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'ckd-creatinine-increased',
    label: 'Chronic Kidney Disease — Creatinine Rose >30% on RAS Inhibitor',
    category: MODIFIER_TREES,
    description: '50-year-old with CKD, still on a RAS inhibitor, prior creatinine test shows a >30% rise — reduces the dose or stops the RAS inhibitor and flags for clinician review.',
    data: {
      current_clinic_sbp: '135', current_clinic_dbp: '92',
      age: '50', risk_factor_count: '2',
      has_ckd: true,
      has_prior_creatinine_test: true,
      still_using_ras_inhibitor: true,
      creatinine_increased_over_30_percent: true,
      facility_capability: 'FULL_RESOURCES',
    },
  },
  {
    id: 'ckd-creatinine-stable',
    label: 'Chronic Kidney Disease — Creatinine Stable on RAS Inhibitor',
    category: MODIFIER_TREES,
    description: '50-year-old with CKD, still on a RAS inhibitor, prior creatinine test shows no significant rise — maintains the current regimen since creatinine is stable.',
    data: {
      current_clinic_sbp: '135', current_clinic_dbp: '92',
      age: '50', risk_factor_count: '2',
      has_ckd: true,
      has_prior_creatinine_test: true,
      still_using_ras_inhibitor: true,
      creatinine_increased_over_30_percent: false,
      facility_capability: 'FULL_RESOURCES',
    },
  },

  // ---- Pregnancy & Postpartum ----
]
