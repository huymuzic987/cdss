import type { EpisodeDefinition } from './followUpComorbidityEpisodeTypes'

export const finalComorbidityEpisodes: EpisodeDefinition[] = [
  {
    slug: 'older-adult',
    patientId: 'medication-follow-up-older-adult-001',
    name: 'Older Adult',
    comorbidity: { age: 82 },
    initialBp: [158, 92],
    followUps: [
      {
        slug: 'follow-up-1-replace',
        label: 'Follow-Up 1: Replace Drug',
        description: 'The monotherapy drug is unusable; replace it within class A and retain the one-drug regimen stage.',
        values: {
          current_regimen_drug_count: 1,
          current_regimen_drug_classes: 'A',
          current_clinic_sbp: 150, current_clinic_dbp: 88,
          assessment_date: '2026-09-01', regimen_effective_date: '2026-08-04',
          drug_replacement_required: true,
        },
      },
      {
        slug: 'follow-up-2-escalate',
        label: 'Follow-Up 2: Escalate',
        description: 'The replacement class-A monotherapy has completed 28 days, but BP remains uncontrolled, allowing normal tree escalation.',
        values: {
          current_regimen_drug_count: 1,
          current_regimen_drug_classes: 'A',
          current_clinic_sbp: 144, current_clinic_dbp: 84,
          assessment_date: '2026-09-29', regimen_effective_date: '2026-09-01',
        },
      },
      {
        slug: 'follow-up-3-controlled',
        label: 'Follow-Up 3: Target Reached',
        description: 'BP reaches the active target after 28 days on A+C+D, so treatment is maintained.',
        values: {
          medication_follow_up_stage: 'ESCALATED_REGIMEN',
          current_regimen_drug_count: 3,
          current_regimen_drug_classes: 'A+C+D',
          current_clinic_sbp: 127, current_clinic_dbp: 77,
          assessment_date: '2026-10-27', regimen_effective_date: '2026-09-29',
        },
      },
    ],
  },
  {
    slug: 'resistant-hypertension',
    patientId: 'medication-follow-up-resistant-hypertension-001',
    name: 'Resistant Hypertension',
    comorbidity: {},
    initialBp: [154, 96],
    followUps: [
      {
        slug: 'follow-up-1-increase-dose',
        label: 'Follow-Up 1: Increase Dose',
        description: 'BP remains uncontrolled after 28 days on low-dose A+D. Dose is not yet adequate, so traversal stops to optimize the two-drug dose without escalating.',
        values: {
          current_clinic_sbp: 146, current_clinic_dbp: 90,
          assessment_date: '2026-11-01', regimen_effective_date: '2026-10-04',
          dose_adequate: false,
        },
      },
      {
        slug: 'follow-up-2-replace-drug',
        label: 'Follow-Up 2: Replace Drug',
        description: 'One drug in the now optimized A+D regimen is unusable. Replace it within its class while retaining A+D and the two-drug stage.',
        values: {
          current_clinic_sbp: 144, current_clinic_dbp: 88,
          assessment_date: '2026-11-29', regimen_effective_date: '2026-11-01',
          drug_replacement_required: true,
        },
      },
      {
        slug: 'follow-up-3-address-adherence',
        label: 'Follow-Up 3: Address Adherence',
        description: 'BP remains uncontrolled after the replacement regimen trial, but adherence is inadequate. Stop traversal and address adherence before escalation.',
        values: {
          current_clinic_sbp: 143, current_clinic_dbp: 87,
          assessment_date: '2026-12-27', regimen_effective_date: '2026-11-29',
          adherence_adequate: false,
        },
      },
      {
        slug: 'follow-up-4-use-three-drugs',
        label: 'Follow-Up 4: Use Three Drugs',
        description: 'After 28 days with adequate dose and adherence on A+D, BP remains uncontrolled and traversal escalates treatment to A+C+D.',
        values: {
          current_clinic_sbp: 141, current_clinic_dbp: 86,
          assessment_date: '2027-01-24', regimen_effective_date: '2026-12-27',
        },
      },
      {
        slug: 'follow-up-5-early',
        label: 'Follow-Up 5: Early Three-Drug Review',
        description: 'Returns only 14 days after starting A+C+D. Traversal stops and continues the regimen until the scheduled reassessment.',
        values: {
          medication_follow_up_stage: 'ESCALATED_REGIMEN',
          current_regimen_drug_count: 3,
          current_regimen_drug_classes: 'A+C+D',
          current_clinic_sbp: 140, current_clinic_dbp: 85,
          assessment_date: '2027-02-07', regimen_effective_date: '2027-01-24',
        },
      },
      {
        slug: 'follow-up-6-resistant-bp-check',
        label: 'Follow-Up 6: Add Resistant-HTN Drug',
        description: 'After a complete A+C+D trial, BP remains uncontrolled. Traversal enters resistant hypertension and stops at Add MRA because the newly prescribed fourth drug has not completed its treatment period.',
        values: {
          facility_capability: 'LIMITED_RESOURCES',
          medication_follow_up_stage: 'ESCALATED_REGIMEN',
          current_regimen_drug_count: 3,
          current_regimen_drug_classes: 'A+C+D',
          current_clinic_sbp: 138, current_clinic_dbp: 84,
          assessment_date: '2027-02-21', regimen_effective_date: '2027-01-24',
          tolerates_mra: true,
        },
      },
      {
        slug: 'follow-up-7-resistant-bp-check',
        label: 'Follow-Up 7: Resistant-HTN BP Check',
        description: 'After 28 days on the four-drug regimen, BP remains uncontrolled. The follow-up gate now permits the resistant-hypertension BP check and traversal reaches referral.',
        values: {
          facility_capability: 'LIMITED_RESOURCES',
          medication_follow_up_stage: 'ESCALATED_REGIMEN',
          current_regimen_drug_count: 4,
          current_regimen_drug_classes: 'A+C+D',
          current_clinic_sbp: 137, current_clinic_dbp: 83,
          assessment_date: '2027-03-21', regimen_effective_date: '2027-02-21',
          tolerates_mra: true,
        },
      },
    ],
  },
]
