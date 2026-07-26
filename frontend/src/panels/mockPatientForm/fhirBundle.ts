// Mirrors src/cdss/api/schemas/fhir_input.py's `input_to_bundle` (the
// reference reverse-mapping). /evaluate now requires `input` to be an HL7
// FHIR R4 Bundle (resourceType == 'Bundle'), so the flat key/value object
// the mock-patient form used to send has to be converted into one here,
// using the exact same resource-mapping contract the backend documents.

import type { JsonObject, JsonValue } from '../../api/types'

const EXT_BASE = 'http://cdss.local/fhir/StructureDefinition'
const EXT_READING_ROLE = `${EXT_BASE}/reading-role`
const EXT_PARAMETER_IS_ARRAY = `${EXT_BASE}/parameter-is-array`

const CS_CLINICAL_FLAG = 'http://cdss.local/fhir/CodeSystem/clinical-flag'
const CS_OBSERVATION_CATEGORY = 'http://terminology.hl7.org/CodeSystem/observation-category'
const CS_CONDITION_CLINICAL = 'http://terminology.hl7.org/CodeSystem/condition-clinical'
const CS_CONDITION_VER_STATUS = 'http://terminology.hl7.org/CodeSystem/condition-ver-status'

const LOINC = 'http://loinc.org'
const LOINC_BP_PANEL = '85354-9'
const LOINC_SBP = '8480-6'
const LOINC_DBP = '8462-4'

const ARRAY_ITEM_NAME = 'item'

const BP_READING_ROLES: Record<string, [string, string]> = {
  current_clinic: ['current_clinic_sbp', 'current_clinic_dbp'],
  previous_visit: ['previous_sbp', 'previous_dbp'],
  clinic_1: ['clinic_1_sbp', 'clinic_1_dbp'],
}

const LAB_OBSERVATIONS: Record<string, [string, string, string]> = {
  acr_mg_mmol: ['9318-7', 'Albumin/Creatinine [Ratio] in Urine', 'mg/mmol'],
  proteinuria_24h_mg: ['2889-4', 'Protein [Mass/time] in 24 hour Urine', 'mg'],
}

const WORKFLOW_FLAG_KEYS = new Set([
  'is_medication_follow_up',
  'is_lifestyle_follow_up',
  'is_treatment_target_not_achieved',
  'is_thrombolysis_candidate',
  'has_dosage_adjustment_request',
  'has_duplicate_drug_class',
  'has_duplicate_ras_inhibitor',
  'has_prior_creatinine_test',
  'has_prior_prescription',
])

function isClinicalFlagKey(key: string): boolean {
  return (key.startsWith('has_') || key.startsWith('is_')) && !WORKFLOW_FLAG_KEYS.has(key)
}

/** Convert the engine's flat `input.*` object into a FHIR R4 Bundle. */
export function flatToBundle(flat: JsonObject): JsonObject {
  const remaining: JsonObject = { ...flat }
  const entries: JsonObject[] = []

  const age = remaining['age']
  delete remaining['age']
  if (age !== undefined && age !== null) {
    entries.push({ resource: patientResource(age) })
  }

  for (const [role, [sbpKey, dbpKey]] of Object.entries(BP_READING_ROLES)) {
    const sbp = remaining[sbpKey]
    const dbp = remaining[dbpKey]
    delete remaining[sbpKey]
    delete remaining[dbpKey]
    if (sbp === undefined && dbp === undefined) continue
    entries.push({ resource: bpObservationResource(role, sbp, dbp) })
  }

  for (const [key, [loincCode, display, unit]] of Object.entries(LAB_OBSERVATIONS)) {
    const value = remaining[key]
    delete remaining[key]
    if (value !== undefined && value !== null) {
      entries.push({ resource: labObservationResource(loincCode, display, unit, value) })
    }
  }

  for (const key of Object.keys(remaining).filter(isClinicalFlagKey)) {
    const value = remaining[key]
    delete remaining[key]
    if (typeof value !== 'boolean') {
      throw new Error(`'${key}' must be a boolean, got ${JSON.stringify(value)}`)
    }
    entries.push({ resource: conditionResource(key, value) })
  }

  if (Object.keys(remaining).length > 0) {
    entries.push({
      resource: {
        resourceType: 'Parameters',
        parameter: Object.entries(remaining).map(([key, value]) => valueToParameter(key, value)),
      },
    })
  }

  return { resourceType: 'Bundle', type: 'collection', entry: entries }
}

function patientResource(age: JsonValue): JsonObject {
  if (typeof age !== 'number' || !Number.isInteger(age)) {
    throw new Error(`'age' must be an integer, got ${JSON.stringify(age)}`)
  }
  const birthYear = new Date().getUTCFullYear() - age
  return { resourceType: 'Patient', birthDate: `${birthYear}-01-01` }
}

function bpObservationResource(role: string, sbp: JsonValue, dbp: JsonValue): JsonObject {
  const components: JsonObject[] = []
  if (sbp !== undefined && sbp !== null) {
    components.push({
      code: { coding: [{ system: LOINC, code: LOINC_SBP, display: 'Systolic blood pressure' }] },
      valueQuantity: { value: sbp, unit: 'mmHg' },
    })
  }
  if (dbp !== undefined && dbp !== null) {
    components.push({
      code: { coding: [{ system: LOINC, code: LOINC_DBP, display: 'Diastolic blood pressure' }] },
      valueQuantity: { value: dbp, unit: 'mmHg' },
    })
  }
  return {
    resourceType: 'Observation',
    status: 'final',
    category: [{ coding: [{ system: CS_OBSERVATION_CATEGORY, code: 'vital-signs' }] }],
    code: { coding: [{ system: LOINC, code: LOINC_BP_PANEL, display: 'Blood pressure panel' }] },
    extension: [{ url: EXT_READING_ROLE, valueCode: role }],
    component: components,
  }
}

function labObservationResource(loincCode: string, display: string, unit: string, value: JsonValue): JsonObject {
  return {
    resourceType: 'Observation',
    status: 'final',
    category: [{ coding: [{ system: CS_OBSERVATION_CATEGORY, code: 'laboratory' }] }],
    code: { coding: [{ system: LOINC, code: loincCode, display }] },
    valueQuantity: { value, unit },
  }
}

function conditionResource(key: string, value: boolean): JsonObject {
  return {
    resourceType: 'Condition',
    clinicalStatus: {
      coding: [{ system: CS_CONDITION_CLINICAL, code: value ? 'active' : 'resolved' }],
    },
    verificationStatus: {
      coding: [{ system: CS_CONDITION_VER_STATUS, code: value ? 'confirmed' : 'refuted' }],
    },
    code: { coding: [{ system: CS_CLINICAL_FLAG, code: key }] },
  }
}

function valueToParameter(name: string, value: JsonValue): JsonObject {
  if (Array.isArray(value)) {
    return {
      name,
      extension: [{ url: EXT_PARAMETER_IS_ARRAY, valueBoolean: true }],
      part: value.map((item) => valueToParameter(ARRAY_ITEM_NAME, item)),
    }
  }
  if (value !== null && typeof value === 'object') {
    return {
      name,
      part: Object.entries(value).map(([key, item]) => valueToParameter(key, item)),
    }
  }
  return { name, ...scalarParameterValue(value) }
}

function scalarParameterValue(value: JsonValue): JsonObject {
  if (typeof value === 'boolean') return { valueBoolean: value }
  if (typeof value === 'number') return Number.isInteger(value) ? { valueInteger: value } : { valueDecimal: value }
  if (typeof value === 'string') return { valueString: value }
  if (value === null) return {}
  throw new Error(`unsupported input value type for FHIR Parameters: ${typeof value}`)
}
