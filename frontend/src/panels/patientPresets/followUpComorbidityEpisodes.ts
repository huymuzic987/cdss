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
