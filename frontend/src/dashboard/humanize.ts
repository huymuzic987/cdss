const LABELS: Record<string, string> = {
  NORMAL_BP: 'Normal blood pressure',
  HIGH_NORMAL_BP: 'High-normal blood pressure',
  GRADE_1_HYPERTENSION: 'Stage 1 hypertension',
  GRADE_2_HYPERTENSION: 'Stage 2 hypertension',
  LOW: 'Low risk',
  MEDIUM: 'Medium risk',
  HIGH: 'High risk',
  FULL_RESOURCES: 'Full-resource facility',
  LIMITED_RESOURCES: 'Limited-resource facility',
  MEDICATION_NOT_SUITABLE: 'Medication not suitable',
  CONDITION_WORSENED: 'Condition worsened',
  SIDE_EFFECTS: 'Side effects',
  OTHER: 'Other reason',
  // ICD-10 codes, matching PatientCondition.icd10_code
  E11: 'Type 2 diabetes',
  N18: 'Chronic kidney disease',
  I25: 'Coronary artery disease',
  I50: 'Heart failure',
  I63: 'Stroke',
  I10: 'Essential hypertension',
  BP_NOT_CONTROLLED: 'Blood pressure not at target',
  OVERDUE: 'Overdue for follow-up',
  RECENT_EARLY_REVISIT: 'Recently returned early',
  male: 'Male',
  female: 'Female',
  unknown: 'Unknown',
  preset: 'Preset patients',
  synthetic: 'Synthetic patients',
  real_test_case: 'Real reference data',
}

/** Turns backend enum codes (e.g. "GRADE_2_HYPERTENSION") into plain-language
 * labels a reader unfamiliar with the codebase can understand at a glance. */
export function humanize(code: string): string {
  return LABELS[code] ?? code.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
