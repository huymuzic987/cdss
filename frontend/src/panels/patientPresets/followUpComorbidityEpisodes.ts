import { flatToBundle } from '../mockPatientForm/fhirBundle'
import { medicationFollowUpBundle } from './followUpEpisode'
import { FOLLOW_UP, type PatientPresetDefinition } from './shared'
import { finalComorbidityEpisodes } from './followUpComorbidityEpisodeDefinitionsC'
import { firstComorbidityEpisodes } from './followUpComorbidityEpisodeDefinitionsA'
import { secondComorbidityEpisodes } from './followUpComorbidityEpisodeDefinitionsB'
import type { EpisodeDefinition } from './followUpComorbidityEpisodeTypes'

const episodes: EpisodeDefinition[] = [
  ...firstComorbidityEpisodes,
  ...secondComorbidityEpisodes,
  ...finalComorbidityEpisodes,
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
