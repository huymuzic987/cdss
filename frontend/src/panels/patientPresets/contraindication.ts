import { CONTRAINDICATION, type PatientPresetBundleDefinition } from './shared'
import { contraindicationCases } from './contraindicationCases'

export const contraindicationPresets: PatientPresetBundleDefinition[] = contraindicationCases.map((caseData) => ({
  id: caseData.id,
  label: caseData.label,
  category: CONTRAINDICATION,
  description: caseData.description,
  bundle: caseData.bundle,
}))
