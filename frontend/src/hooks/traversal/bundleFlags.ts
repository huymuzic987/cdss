import type { JsonObject } from '../../api/types'

const CLINICAL_FLAG_SYSTEM = 'http://cdss.local/fhir/CodeSystem/clinical-flag'
const VERIFICATION_SYSTEM = 'http://terminology.hl7.org/CodeSystem/condition-ver-status'

export function updateBundleClinicalFlag(bundle: JsonObject, key: string, value: boolean): JsonObject {
  if (bundle.resourceType !== 'Bundle' || !Array.isArray(bundle.entry)) {
    return { ...bundle, [key]: value }
  }

  const entries = [...bundle.entry] as JsonObject[]
  const patient = entries
    .map((entry) => entry.resource as JsonObject | undefined)
    .find((resource) => resource?.resourceType === 'Patient')
  const patientId = typeof patient?.id === 'string' ? patient.id : 'simulated-patient'
  let foundCondition = false

  const updatedEntries = entries.map((entry) => {
    const resource = entry.resource as JsonObject | undefined
    const coding = resource?.resourceType === 'Condition'
      ? ((resource.code as JsonObject | undefined)?.coding as JsonObject[] | undefined)
      : undefined
    if (!coding?.some((item) => item.system === CLINICAL_FLAG_SYSTEM && item.code === key)) return entry
    foundCondition = true
    return {
      ...entry,
      resource: {
        ...resource,
        verificationStatus: { coding: [{ system: VERIFICATION_SYSTEM, code: value ? 'confirmed' : 'refuted' }] },
      },
    }
  })

  if (!foundCondition) {
    updatedEntries.push({
      resource: {
        resourceType: 'Condition',
        id: `${patientId}-${key}`,
        subject: { reference: `Patient/${patientId}` },
        verificationStatus: { coding: [{ system: VERIFICATION_SYSTEM, code: value ? 'confirmed' : 'refuted' }] },
        code: { coding: [{ system: CLINICAL_FLAG_SYSTEM, code: key }] },
      },
    })
  }
  return { ...bundle, entry: updatedEntries }
}
