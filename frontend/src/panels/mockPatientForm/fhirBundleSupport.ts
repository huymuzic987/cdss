import type { JsonObject, JsonValue } from '../../api/types'

export const EXT_BASE = 'http://cdss.local/fhir/StructureDefinition'
export const EXT_READING_ROLE = `${EXT_BASE}/reading-role`
export const EXT_RISK_FACTOR_COUNT = `${EXT_BASE}/risk-factor-count`
export const EXT_FACILITY_CAPABILITY = `${EXT_BASE}/facility-capability`
export const EXT_INPUT_PREFIX = `${EXT_BASE}/input/`
export const CS_CLINICAL_FLAG = 'http://cdss.local/fhir/CodeSystem/clinical-flag'
export const CS_CONDITION_VER_STATUS = 'http://terminology.hl7.org/CodeSystem/condition-ver-status'
export const LOINC = 'http://loinc.org'
export const LOINC_SBP = '8459-0'
export const LOINC_DBP = '8462-4'

export const BP_KEYS: Record<string, [string, string]> = {
  current_clinic: ['current_clinic_sbp', 'current_clinic_dbp'],
  previous: ['previous_sbp', 'previous_dbp'],
  home: ['home_sbp', 'home_dbp'],
}

export const LABS: Record<string, [string, string, string]> = {
  eGFR: ['98979-8', 'Estimated glomerular filtration rate', 'mL/min'],
  serum_potassium: ['6298-4', 'Potassium [Moles/volume] in Serum or Plasma', 'mmol/L'],
  acr_mg_mmol: ['9318-7', 'Albumin/Creatinine [Ratio] in Urine', 'mg/mmol'],
  proteinuria_24h_mg: ['2889-4', 'Protein [Mass/time] in 24 hour Urine', 'mg'],
}

export function appendBpEntries(entries: JsonObject[], flat: JsonObject, patientId: string, role: string, encounterId?: string, explicitRole?: string): void {
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

export function observationResource(patientId: string, id: string, code: string, display: string, value: number, unit: string, encounterId?: string, role?: string, effectiveDateTime = '2024-02-01'): JsonObject {
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

export function encounterResource(patientId: string, suffix: string, start: string, extension: JsonObject[]): JsonObject {
  return {
    resourceType: 'Encounter', id: `${patientId}-${suffix}`, status: 'finished',
    class: { system: 'http://terminology.hl7.org/CodeSystem/v3-ActCode', code: 'AMB' },
    subject: { reference: `Patient/${patientId}` }, period: { start }, extension,
  }
}

export function conditionResource(patientId: string, key: string, active: boolean): JsonObject {
  return {
    resourceType: 'Condition', id: `${patientId}-${key}`, subject: { reference: `Patient/${patientId}` },
    verificationStatus: { coding: [{ system: CS_CONDITION_VER_STATUS, code: active ? 'confirmed' : 'refuted' }] },
    code: { coding: [{ system: CS_CLINICAL_FLAG, code: key }] },
  }
}

export function applyExtensions(value: JsonValue | undefined, flat: JsonObject): void {
  for (const raw of asArray(value)) {
    const extension = asObject(raw)
    if (!extension || typeof extension.url !== 'string') continue
    const typedValue = typedExtensionValue(extension)
    if (typedValue === undefined) continue
    if (extension.url === EXT_RISK_FACTOR_COUNT) flat.risk_factor_count = typedValue
    else if (extension.url === EXT_FACILITY_CAPABILITY) flat.facility_capability = typedValue
    else if (extension.url.startsWith(EXT_INPUT_PREFIX)) flat[extension.url.slice(EXT_INPUT_PREFIX.length)] = typedValue
  }
}

export function extensionValue(value: JsonValue | undefined, url: string): JsonValue | undefined {
  const extension = asArray(value).map(asObject).find((entry) => entry?.url === url)
  return extension ? typedExtensionValue(extension) : undefined
}

function typedExtensionValue(extension: JsonObject): JsonValue | undefined {
  for (const key of ['valueBoolean', 'valueInteger', 'valueDecimal', 'valueString', 'valueCode']) {
    if (extension[key] !== undefined) return extension[key]
  }
  return undefined
}

export function scalarExtensionValue(value: JsonValue): JsonObject | null {
  if (typeof value === 'boolean') return { valueBoolean: value }
  if (typeof value === 'number') return Number.isInteger(value) ? { valueInteger: value } : { valueDecimal: value }
  if (typeof value === 'string') return { valueString: value }
  return null
}

export function hasPair(flat: JsonObject, role: string): boolean {
  const keys = BP_KEYS[role]
  return Boolean(keys && typeof flat[keys[0]] === 'number' && typeof flat[keys[1]] === 'number')
}

export function take(object: JsonObject, key: string): JsonValue | undefined {
  const value = object[key]
  delete object[key]
  return value
}

export function asObject(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonObject : null
}

export function asArray(value: unknown): JsonValue[] {
  return Array.isArray(value) ? value : []
}
