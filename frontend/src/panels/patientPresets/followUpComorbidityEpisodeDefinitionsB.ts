import type { EpisodeDefinition } from './followUpComorbidityEpisodeTypes'

export const secondComorbidityEpisodes: EpisodeDefinition[] = [
  {
    slug: 'cad',
    patientId: 'medication-follow-up-cad-001',
    name: 'Coronary Artery Disease',
    comorbidity: {
      has_coronary_artery_disease: true,
      has_cardiovascular_disease: true,
      has_ccs_revasc: true,
    },
    initialBp: [152, 96],
    followUps: [
      {
        slug: 'follow-up-1-address-adherence',
        label: 'Follow-Up 1: Address Adherence',
        description: 'BP remains uncontrolled after 28 days on A+D, but adherence is inadequate. Stop before escalation and address adherence first.',
        values: {
          current_clinic_sbp: 146, current_clinic_dbp: 92,
          assessment_date: '2026-06-01', regimen_effective_date: '2026-05-04',
          adherence_adequate: false,
        },
      },
      {
        slug: 'follow-up-2-escalate',
        label: 'Follow-Up 2: Escalate',
        description: 'After a new adequate 28-day A+D trial with adequate dose and adherence, BP remains uncontrolled and traversal may escalate to A+C+D.',
        values: {
          current_clinic_sbp: 141, current_clinic_dbp: 87,
          assessment_date: '2026-06-29', regimen_effective_date: '2026-06-01',
        },
      },
      {
        slug: 'follow-up-3-controlled',
        label: 'Follow-Up 3: Target Reached',
        description: 'After 28 days on A+C+D, BP reaches target and the escalated regimen is maintained.',
        values: {
          medication_follow_up_stage: 'ESCALATED_REGIMEN',
          current_regimen_drug_count: 3,
          current_regimen_drug_classes: 'A+C+D',
          current_clinic_sbp: 127, current_clinic_dbp: 77,
          assessment_date: '2026-07-27', regimen_effective_date: '2026-06-29',
        },
      },
    ],
  },
  {
    slug: 'heart-failure',
    patientId: 'medication-follow-up-heart-failure-001',
    name: 'Heart Failure',
    comorbidity: { has_heart_failure: true, has_hfmref: true },
    initialBp: [150, 94],
    followUps: [
      {
        slug: 'follow-up-1-early',
        label: 'Follow-Up 1: Early Arrival',
        description: 'Returns after 14 days on A+D without a drug change; traversal stops until the scheduled reassessment.',
        values: {
          current_clinic_sbp: 144, current_clinic_dbp: 90,
          assessment_date: '2026-02-15', regimen_effective_date: '2026-02-01',
        },
      },
      {
        slug: 'follow-up-2-escalate',
        label: 'Follow-Up 2: Escalate',
        description: 'At 28 days, BP remains uncontrolled on adequate A+D treatment and traversal escalates to A+C+D.',
        values: {
          current_clinic_sbp: 140, current_clinic_dbp: 86,
          assessment_date: '2026-03-01', regimen_effective_date: '2026-02-01',
        },
      },
      {
        slug: 'follow-up-3-controlled',
        label: 'Follow-Up 3: Target Reached',
        description: 'After an adequate A+B+C+D trial, BP reaches target and the current heart-failure regimen is maintained.',
        values: {
          medication_follow_up_stage: 'ESCALATED_REGIMEN',
          current_regimen_drug_count: 4,
          current_regimen_drug_classes: 'A+B+C+D',
          current_clinic_sbp: 125, current_clinic_dbp: 75,
          assessment_date: '2026-03-29', regimen_effective_date: '2026-03-01',
        },
      },
    ],
  },
]
