import { formToPayload } from './mockPatientForm/payload'
import { DEFAULT_FORM } from './mockPatientForm/types'
import { cardioModifierPresets } from './patientPresets/modifiersCardio'
import { demographicPresets } from './patientPresets/demographic'
import { diagnosisPresets } from './patientPresets/diagnosis'
import { followUpPresets } from './patientPresets/followUp'
import { comorbidityFollowUpEpisodePresets } from './patientPresets/followUpComorbidityEpisodes'
import {
  pregnancyFollowUpPresets,
  pregnancyPresets,
} from './patientPresets/pregnancy'
import { renalModifierPresets } from './patientPresets/modifiersRenal'
import { contraindicationPresets } from './patientPresets/contraindication'
import type { PatientPreset, PatientPresetDefinition } from './patientPresets/shared'

export type { PatientPreset } from './patientPresets/shared'

const definitions: PatientPresetDefinition[] = [
  ...diagnosisPresets,
  ...demographicPresets,
  ...followUpPresets,
  ...comorbidityFollowUpEpisodePresets,
  ...cardioModifierPresets,
  ...renalModifierPresets,
  ...contraindicationPresets,
  ...pregnancyPresets,
  ...pregnancyFollowUpPresets,
]

export const PATIENT_PRESETS: PatientPreset[] = definitions.map((definition) => {
  if ('bundle' in definition) return definition
  const { data, ...preset } = definition
  return {
    ...preset,
    bundle: formToPayload({ ...DEFAULT_FORM, ...data }),
  }
})
