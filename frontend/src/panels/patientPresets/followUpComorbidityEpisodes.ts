import type { JsonObject } from '../../api/types'
import { flatToBundle } from '../mockPatientForm/fhirBundle'
import { medicationFollowUpBundle } from './followUpEpisode'
import { FOLLOW_UP, type PatientPresetDefinition } from './shared'

interface EpisodeDefinition {
  slug: string
  patientId: string
  name: string
  comorbidity: JsonObject
  initialBp: [number, number]
  followUps: Array<{
    slug: string
    label: string
    description: string
    values: JsonObject
  }>
}

const episodes: EpisodeDefinition[] = [
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

export const comorbidityFollowUpEpisodePresets: PatientPresetDefinition[] = episodes.flatMap(
  (episode) => {
    const [sbp, dbp] = episode.initialBp
    const shared = {
      facility_capability: 'FULL_RESOURCES',
      age: 58,
      risk_factor_count: 3,
      ...episode.comorbidity,
    }

    return [
      {
        id: `comorbidity-episode-${episode.slug}-initial`,
        label: `${episode.name} Episode — Initial Visit`,
        category: FOLLOW_UP,
        description: `Initial uncontrolled-hypertension visit for ${episode.patientId}; routes through the ${episode.name} comorbidity branch before treatment selection.`,
        bundle: flatToBundle({
          ...shared,
          current_clinic_sbp: sbp,
          current_clinic_dbp: dbp,
        }, episode.patientId),
      },
      ...episode.followUps.map((followUp) => ({
        id: `comorbidity-episode-${episode.slug}-${followUp.slug}`,
        label: `${episode.name} Episode — ${followUp.label}`,
        category: FOLLOW_UP,
        description: followUp.description,
        bundle: medicationFollowUpBundle({
          ...shared,
          ...followUp.values,
        }, episode.patientId),
      })),
    ]
  },
)
