import type { JsonObject } from '../../api/types'
import {
  applyExtensions,
  appendBpEntries,
  asArray,
  asObject,
  BP_KEYS,
  conditionResource,
  CS_CLINICAL_FLAG,
  encounterResource,
  EXT_FACILITY_CAPABILITY,
  EXT_INPUT_PREFIX,
  EXT_READING_ROLE,
  EXT_RISK_FACTOR_COUNT,
  extensionValue,
  hasPair,
  LABS,
  LOINC,
  LOINC_DBP,
  LOINC_SBP,
  observationResource,
  scalarExtensionValue,
  take,
} from './fhirBundleSupport'

export function flatToBundle(flat: JsonObject, patientId = 'simulated-patient'): JsonObject {
  const remaining: JsonObject = { ...flat }
  const entries: JsonObject[] = []
  const patientExtensions: JsonObject[] = []
  const age = take(remaining, 'age')
  const riskFactors = take(remaining, 'risk_factor_count')
  if (typeof riskFactors === 'number') {
    patientExtensions.push({ url: EXT_RISK_FACTOR_COUNT, valueInteger: riskFactors })
  }

  const booleans = Object.keys(remaining).filter((key) => typeof remaining[key] === 'boolean')
  for (const key of booleans) {
    entries.push({
      fullUrl: `Condition/${patientId}-${key}`,
      resource: conditionResource(patientId, key, remaining[key] === true),
    })
    delete remaining[key]
  }

  const hasFollowUp = hasPair(remaining, 'previous') && hasPair(remaining, 'current_clinic')
  if (hasFollowUp) {
    entries.push({ resource: encounterResource(patientId, 'previous', '2024-01-01', []) })
    entries.push({ resource: encounterResource(patientId, 'current', '2024-02-01', []) })
    appendBpEntries(entries, remaining, patientId, 'previous', `${patientId}-previous`, undefined)
    appendBpEntries(entries, remaining, patientId, 'current_clinic', `${patientId}-current`, undefined)
    delete remaining['clinic_1_sbp']
    delete remaining['clinic_1_dbp']
  } else {
    for (const role of Object.keys(BP_KEYS)) {
      appendBpEntries(entries, remaining, patientId, role, undefined, role)
    }
  }

  for (const [key, [code, display, unit]] of Object.entries(LABS)) {
    const value = take(remaining, key)
    if (typeof value === 'number') {
      entries.push({ resource: observationResource(patientId, `${patientId}-${key}`, code, display, value, unit) })
    }
  }

  const facility = take(remaining, 'facility_capability')
  if (typeof facility === 'string' && facility) {
    patientExtensions.push({ url: EXT_FACILITY_CAPABILITY, valueString: facility })
  }
  for (const [key, value] of Object.entries(remaining)) {
    const extensionValue = scalarExtensionValue(value)
    if (extensionValue) patientExtensions.push({ url: `${EXT_INPUT_PREFIX}${key}`, ...extensionValue })
  }

  entries.unshift({
    fullUrl: `Patient/${patientId}`,
    resource: {
      resourceType: 'Patient', id: patientId,
      ...(typeof age === 'number' ? { birthDate: `${new Date().getUTCFullYear() - Math.trunc(age)}-01-01` } : {}),
      ...(patientExtensions.length ? { extension: patientExtensions } : {}),
    },
  })
  return { resourceType: 'Bundle', type: 'collection', entry: entries }
}

/** Decode canonical simulator Bundles so stored FHIR presets remain editable. */
export function bundleToFlat(bundle: JsonObject): JsonObject {
  const flat: JsonObject = {}
  const resources = Array.isArray(bundle['entry'])
    ? bundle['entry'].map((entry) => asObject(asObject(entry)?.resource)).filter((value): value is JsonObject => value !== null)
    : []
  const patient = resources.find((resource) => resource.resourceType === 'Patient')
  if (patient) {
    if (typeof patient.birthDate === 'string') flat.age = new Date().getUTCFullYear() - Number(patient.birthDate.slice(0, 4))
    applyExtensions(patient.extension, flat)
  }
  for (const condition of resources.filter((resource) => resource.resourceType === 'Condition')) {
    const codings = asArray(asObject(condition.code)?.coding)
    const flag = codings.map(asObject).find((coding) => coding?.system === CS_CLINICAL_FLAG)?.code
    if (typeof flag === 'string') {
      const verification = asArray(asObject(condition.verificationStatus)?.coding).map(asObject)
      flat[flag] = !verification.some((coding) => coding?.code === 'refuted')
    }
  }
  const encounters = resources
    .filter((resource) => resource.resourceType === 'Encounter')
    .sort((left, right) => String(asObject(left.period)?.start).localeCompare(String(asObject(right.period)?.start)))
  const encounterRole = new Map<string, string>()
  if (encounters.length >= 2) {
    encounterRole.set(String(encounters.at(-2)?.id), 'previous')
    encounterRole.set(String(encounters.at(-1)?.id), 'current_clinic')
  }
  for (const observation of resources.filter((resource) => resource.resourceType === 'Observation')) {
    const code = asArray(asObject(observation.code)?.coding).map(asObject).find((coding) => coding?.system === LOINC)?.code
    const value = asObject(observation.valueQuantity)?.value
    if (typeof value !== 'number') continue
    const encounterId = String(asObject(observation.encounter)?.reference ?? '').split('/').at(-1)
    const explicitRole = extensionValue(observation.extension, EXT_READING_ROLE)
    const role = (typeof explicitRole === 'string' ? explicitRole : encounterRole.get(encounterId ?? '')) ?? 'clinic_1'
    if (code === LOINC_SBP) flat[BP_KEYS[role]?.[0] ?? 'clinic_1_sbp'] = value
    else if (code === LOINC_DBP) flat[BP_KEYS[role]?.[1] ?? 'clinic_1_dbp'] = value
    else {
      const lab = Object.entries(LABS).find(([, metadata]) => metadata[0] === code)
      if (lab) flat[lab[0]] = value
    }
  }
  return flat
}
