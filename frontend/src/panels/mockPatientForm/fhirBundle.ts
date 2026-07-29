import type { JsonObject, JsonValue } from '../../api/types'

const EXT_BASE = 'http://cdss.local/fhir/StructureDefinition'
const EXT_READING_ROLE = `${EXT_BASE}/reading-role`
const EXT_RISK_FACTOR_COUNT = `${EXT_BASE}/risk-factor-count`
const EXT_FACILITY_CAPABILITY = `${EXT_BASE}/facility-capability`
const EXT_INPUT_PREFIX = `${EXT_BASE}/input/`
const CS_CLINICAL_FLAG = 'http://cdss.local/fhir/CodeSystem/clinical-flag'
const CS_CONDITION_VER_STATUS = 'http://terminology.hl7.org/CodeSystem/condition-ver-status'
const LOINC = 'http://loinc.org'
const LOINC_SBP = '8459-0'
const LOINC_DBP = '8462-4'

const BP_KEYS: Record<string, [string, string]> = {
  clinic_1: ['clinic_1_sbp', 'clinic_1_dbp'],
  current_clinic: ['current_clinic_sbp', 'current_clinic_dbp'],
  previous: ['previous_sbp', 'previous_dbp'],
  home: ['home_sbp', 'home_dbp'],
}

const LABS: Record<string, [string, string, string]> = {
  acr_mg_mmol: ['9318-7', 'Albumin/Creatinine [Ratio] in Urine', 'mg/mmol'],
  proteinuria_24h_mg: ['2889-4', 'Protein [Mass/time] in 24 hour Urine', 'mg'],
}

/** Build the canonical clinical Bundle accepted by /evaluate and /fhir/import. */
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

function appendBpEntries(entries: JsonObject[], flat: JsonObject, patientId: string, role: string, encounterId?: string, explicitRole?: string): void {
  const keys = BP_KEYS[role]
  if (!keys) return
  const sbp = take(flat, keys[0])
  const dbp = take(flat, keys[1])
  if (sbp === undefined && dbp === undefined) return
  if (typeof sbp !== 'number' || typeof dbp !== 'number') throw new Error(`${role} requires both systolic and diastolic values`)
  const effective = encounterId?.endsWith('previous') ? '2024-01-01' : '2024-02-01'
  entries.push({ resource: observationResource(patientId, `${patientId}-${role}-sbp`, LOINC_SBP, 'Sitting systolic blood pressure', sbp, 'mmHg', encounterId, explicitRole, effective) })
  entries.push({ resource: observationResource(patientId, `${patientId}-${role}-dbp`, LOINC_DBP, 'Diastolic blood pressure', dbp, 'mmHg', encounterId, explicitRole, effective) })
}

function observationResource(patientId: string, id: string, code: string, display: string, value: number, unit: string, encounterId?: string, role?: string, effectiveDateTime = '2024-02-01'): JsonObject {
  return {
    resourceType: 'Observation', id, status: 'final',
    code: { coding: [{ system: LOINC, code, display }] },
    subject: { reference: `Patient/${patientId}` },
    ...(encounterId ? { encounter: { reference: `Encounter/${encounterId}` } } : {}),
    effectiveDateTime,
    ...(role ? { extension: [{ url: EXT_READING_ROLE, valueCode: role }] } : {}),
    valueQuantity: { value, unit, system: 'http://unitsofmeasure.org', code: unit === 'mmHg' ? 'mm[Hg]' : unit },
  }
}

function encounterResource(patientId: string, suffix: string, start: string, extension: JsonObject[]): JsonObject {
  return {
    resourceType: 'Encounter', id: `${patientId}-${suffix}`, status: 'finished',
    class: { system: 'http://terminology.hl7.org/CodeSystem/v3-ActCode', code: 'AMB' },
    subject: { reference: `Patient/${patientId}` }, period: { start }, extension,
  }
}

function conditionResource(patientId: string, key: string, active: boolean): JsonObject {
  return {
    resourceType: 'Condition', id: `${patientId}-${key}`, subject: { reference: `Patient/${patientId}` },
    verificationStatus: { coding: [{ system: CS_CONDITION_VER_STATUS, code: active ? 'confirmed' : 'refuted' }] },
    code: { coding: [{ system: CS_CLINICAL_FLAG, code: key }] },
  }
}

function applyExtensions(value: JsonValue | undefined, flat: JsonObject): void {
  for (const raw of asArray(value)) {
    const extension = asObject(raw)
    if (!extension || typeof extension.url !== 'string') continue
    const value = typedExtensionValue(extension)
    if (value === undefined) continue
    if (extension.url === EXT_RISK_FACTOR_COUNT) flat.risk_factor_count = value
    else if (extension.url === EXT_FACILITY_CAPABILITY) flat.facility_capability = value
    else if (extension.url.startsWith(EXT_INPUT_PREFIX)) flat[extension.url.slice(EXT_INPUT_PREFIX.length)] = value
  }
}

function extensionValue(value: JsonValue | undefined, url: string): JsonValue | undefined {
  const extension = asArray(value).map(asObject).find((entry) => entry?.url === url)
  return extension ? typedExtensionValue(extension) : undefined
}

function typedExtensionValue(extension: JsonObject): JsonValue | undefined {
  for (const key of ['valueBoolean', 'valueInteger', 'valueDecimal', 'valueString', 'valueCode']) {
    if (extension[key] !== undefined) return extension[key]
  }
  return undefined
}

function scalarExtensionValue(value: JsonValue): JsonObject | null {
  if (typeof value === 'boolean') return { valueBoolean: value }
  if (typeof value === 'number') return Number.isInteger(value) ? { valueInteger: value } : { valueDecimal: value }
  if (typeof value === 'string') return { valueString: value }
  return null
}

function hasPair(flat: JsonObject, role: string): boolean {
  const keys = BP_KEYS[role]
  return Boolean(keys && typeof flat[keys[0]] === 'number' && typeof flat[keys[1]] === 'number')
}

function take(object: JsonObject, key: string): JsonValue | undefined {
  const value = object[key]
  delete object[key]
  return value
}

function asObject(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonObject : null
}

function asArray(value: unknown): JsonValue[] {
  return Array.isArray(value) ? value : []
}
