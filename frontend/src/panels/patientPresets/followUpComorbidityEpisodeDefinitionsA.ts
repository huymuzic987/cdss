import type { EpisodeDefinition } from './followUpComorbidityEpisodeTypes'

export const firstComorbidityEpisodes: EpisodeDefinition[] = [
  {
    slug: 'ckd',
    patientId: 'medication-follow-up-ckd-001',
    name: 'CKD',
    comorbidity: { has_ckd: true, has_ckd_stage_3_or_higher: true },
    initialBp: [148, 94],
    followUps: [
      {
        slug: 'follow-up-1-replace',
        label: 'Follow-Up 1: Replace Drug',
        description: 'After 28 days on A+D, BP remains uncontrolled and one drug is unusable. Replace that drug within its class without escalating the two-drug stage.',
        values: {
          current_clinic_sbp: 144, current_clinic_dbp: 90,
          assessment_date: '2026-02-01', regimen_effective_date: '2026-01-04',
          drug_replacement_required: true,
        },
      },
      {
        slug: 'follow-up-2-escalate',
        label: 'Follow-Up 2: Escalate',
        description: 'The replacement A+D regimen has completed another 28-day trial and BP remains uncontrolled, allowing normal traversal to the three-drug escalation.',
        values: {
          current_clinic_sbp: 140, current_clinic_dbp: 86,
          assessment_date: '2026-03-01', regimen_effective_date: '2026-02-01',
        },
      },
      {
        slug: 'follow-up-3-controlled',
        label: 'Follow-Up 3: Target Reached',
        description: 'After 28 days on the escalated A+C+D regimen, BP reaches target and traversal maintains treatment.',
        values: {
          medication_follow_up_stage: 'ESCALATED_REGIMEN',
          current_regimen_drug_count: 3,
          current_regimen_drug_classes: 'A+C+D',
          current_clinic_sbp: 126, current_clinic_dbp: 76,
          assessment_date: '2026-03-29', regimen_effective_date: '2026-03-01',
        },
      },
    ],
  },
  {
    slug: 'type2-diabetes',
    patientId: 'medication-follow-up-type2-diabetes-001',
    name: 'Type 2 Diabetes',
    comorbidity: { has_type_2_diabetes: true, has_cardiovascular_disease: true },
    initialBp: [146, 90],
    followUps: [
      {
        slug: 'follow-up-1-early',
        label: 'Follow-Up 1: Early Arrival',
        description: 'Returns 14 days into A+C with no medication change. Stop traversal and continue the current regimen until reassessment.',
        values: {
          current_regimen_drug_classes: 'A+C',
          current_clinic_sbp: 138, current_clinic_dbp: 84,
          assessment_date: '2026-04-15', regimen_effective_date: '2026-04-01',
        },
      },
      {
        slug: 'follow-up-2-controlled',
        label: 'Follow-Up 2: Target Reached',
        description: 'At the 28-day reassessment on A+C, BP is controlled. Continue normal target-reached traversal and maintain the regimen.',
        values: {
          current_regimen_drug_classes: 'A+C',
          current_clinic_sbp: 126, current_clinic_dbp: 76,
          assessment_date: '2026-04-29', regimen_effective_date: '2026-04-01',
        },
      },
      {
        slug: 'follow-up-3-maintain',
        label: 'Follow-Up 3: Continue Control',
        description: 'A later scheduled review confirms that BP remains controlled on A+C, so the current regimen is maintained.',
        values: {
          current_regimen_drug_classes: 'A+C',
          current_clinic_sbp: 124, current_clinic_dbp: 74,
          assessment_date: '2026-05-27', regimen_effective_date: '2026-04-29',
        },
      },
    ],
  },
]
