import { formToPayload } from '../frontend/src/panels/mockPatientForm/payload'
import { DEFAULT_FORM } from '../frontend/src/panels/mockPatientForm/types'
import { cardioModifierPresets } from '../frontend/src/panels/patientPresets/modifiersCardio'
import { demographicPresets } from '../frontend/src/panels/patientPresets/demographic'
import { diagnosisPresets } from '../frontend/src/panels/patientPresets/diagnosis'
import { followUpPresets } from '../frontend/src/panels/patientPresets/followUp'
import { comorbidityFollowUpEpisodePresets } from '../frontend/src/panels/patientPresets/followUpComorbidityEpisodes'
import { pregnancyFollowUpPresets, pregnancyPresets } from '../frontend/src/panels/patientPresets/pregnancy'
import { renalModifierPresets } from '../frontend/src/panels/patientPresets/modifiersRenal'
import { contraindicationPresets } from '../frontend/src/panels/patientPresets/contraindication'
import type { PatientPreset, PatientPresetDefinition } from '../frontend/src/panels/patientPresets/shared'

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

export const LEGACY_PATIENT_PRESETS: PatientPreset[] = definitions.map((definition) => {
  if ('bundle' in definition) return definition
  const { data, ...preset } = definition
  return { ...preset, bundle: formToPayload({ ...DEFAULT_FORM, ...data }) }
})
