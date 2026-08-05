import type { JsonObject } from '../../api/types'

const ICD10 = 'http://hl7.org/fhir/sid/icd-10'
const SNOMED = 'http://snomed.info/sct'
const LOINC = 'http://loinc.org'
const UCUM = 'http://unitsofmeasure.org'
const ACT_CODE = 'http://terminology.hl7.org/CodeSystem/v3-ActCode'
const CLINICAL_FLAG = 'http://cdss.local/fhir/CodeSystem/clinical-flag'
const INPUT_BASE = 'http://cdss.local/fhir/StructureDefinition/input/'
const READING_ROLE = 'http://cdss.local/fhir/StructureDefinition/reading-role'

export type InputValue = boolean | number | string

export interface ConditionSpec {
  key: string
  text: string
  icd10: string
  snomed?: string
}

export interface LabSpec {
  key: string
  code: string
  value: number
  unit: string
  ucumCode: string
}

/**
 * A contraindication preset starts with a real, already-working form preset.
 * These fields are the additional clinical facts layered onto that source
 * bundle; keeping the source bundle intact prevents test presets from
 * accidentally omitting required traversal inputs.
 */
export interface ContraindicationAugmentation {
  conditions: ConditionSpec[]
  medications: string[]
  inputs?: Record<string, InputValue>
  homeBp?: [number, number]
  labs?: LabSpec[]
}

// Pregnancy-tree numeric comparisons are strict runtime paths. A missing
// measurement must be represented as a neutral value in test Bundles so a
// branch that does not use it can still be evaluated safely.
const PREGNANCY_INPUT_DEFAULTS: Record<string, InputValue> = {
  proteinuria_24h_mg: 0,
  acr_mg_mmol: 0,
  weeks_persisting_postpartum: 0,
  weeks_resolved_postpartum: 0,
}

export function augmentWorkingBundle(bundle: JsonObject, patientId: string, augmentation: ContraindicationAugmentation): JsonObject {
  const entries = Array.isArray(bundle.entry)
    ? bundle.entry.filter((entry): entry is JsonObject => Boolean(entry && typeof entry === 'object'))
    : []
  const patientEntry = entries.find((entry) => {
    const resource = entry.resource
    return Boolean(resource && typeof resource === 'object' && (resource as JsonObject).resourceType === 'Patient')
  })
  const patient = patientEntry?.resource as JsonObject | undefined
  if (!patient) throw new Error(`Contraindication preset ${patientId} has no Patient resource`)

  for (const entry of entries) {
    const resource = entry.resource as JsonObject | undefined
    const coding = resource?.code && typeof resource.code === 'object'
      ? (resource.code as JsonObject).coding
      : undefined
    const flag = Array.isArray(coding)
      ? coding.find((item) => item && typeof item === 'object' && (item as JsonObject).system === CLINICAL_FLAG)
      : undefined
    const key = flag && typeof flag === 'object' ? (flag as JsonObject).code : undefined
    if (resource?.resourceType === 'Condition' && typeof key === 'string' && augmentation.inputs?.[key] === true) {
      resource.verificationStatus = { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/condition-ver-status', code: 'confirmed' }] }
    }
  }

  const inputValues = augmentation.inputs?.is_pregnant === true
    ? { ...PREGNANCY_INPUT_DEFAULTS, ...augmentation.inputs }
    : augmentation.inputs ?? {}
  const patientExtensions = Array.isArray(patient.extension)
    ? patient.extension.filter((extension): extension is JsonObject => Boolean(extension && typeof extension === 'object'))
    : []
  for (const [key, value] of Object.entries(inputValues)) {
    patientExtensions.push({ url: `${INPUT_BASE}${key}`, ...typedExtension(value) })
  }
  if (patientExtensions.length) patient.extension = patientExtensions

  const patientRef = `Patient/${patientId}`
  const encounter = entries
    .map((entry) => entry.resource)
    .find((resource) => resource && typeof resource === 'object' && (resource as JsonObject).resourceType === 'Encounter') as JsonObject | undefined
  const encounterId = typeof encounter?.id === 'string' ? encounter.id : `${patientId}-contraindication-encounter`
  const encounterRef = `Encounter/${encounterId}`
  if (!encounter) {
    const resource: JsonObject = {
      resourceType: 'Encounter',
      id: encounterId,
      status: 'finished',
      class: { system: ACT_CODE, code: 'AMB', display: 'ambulatory' },
      subject: { reference: patientRef },
      period: { start: '2026-01-15' },
    }
    for (const entry of entries) {
      const observation = entry.resource as JsonObject | undefined
      if (observation?.resourceType !== 'Observation' || observation.encounter) continue
      const role = Array.isArray(observation.extension)
        ? observation.extension.some((item) => item && typeof item === 'object' && (item as JsonObject).url === READING_ROLE && (item as JsonObject).valueCode === 'home')
        : false
      if (!role) observation.encounter = { reference: encounterRef }
    }
    entries.push({ fullUrl: `http://cdss.local/fhir/Encounter/${encounterId}`, resource })
  }

  for (const condition of augmentation.conditions) {
    const resource = conditionResource(patientId, condition)
    entries.push({ fullUrl: `http://cdss.local/fhir/Condition/${String(resource.id)}`, resource })
  }
  for (const medication of augmentation.medications) {
    const resource = medicationRequest(patientId, encounterRef, medication)
    entries.push({ fullUrl: `http://cdss.local/fhir/MedicationRequest/${String(resource.id)}`, resource })
  }
  for (const lab of augmentation.labs ?? []) {
    const resource = observation(patientId, encounterRef, lab.key, lab.code, lab.value, lab.unit, lab.ucumCode)
    entries.push({ fullUrl: `http://cdss.local/fhir/Observation/${String(resource.id)}`, resource })
  }
  const homeBp = augmentation.homeBp ?? [130, 80]
  if (homeBp) {
    const hasHomeObservation = entries.some((entry) => {
      const resource = entry.resource as JsonObject | undefined
      const extensions = Array.isArray(resource?.extension) ? resource.extension : []
      return resource?.resourceType === 'Observation' && extensions.some((extension) => {
        const value = extension as JsonObject
        return value.url === READING_ROLE && value.valueCode === 'home'
      })
    })
    if (!hasHomeObservation) {
      entries.push({
        fullUrl: `http://cdss.local/fhir/Observation/${patientId}-obs-home-sbp`,
        resource: observation(patientId, encounterRef, 'home-sbp', '8459-0', homeBp[0], 'mmHg', 'mm[Hg]', 'home'),
      })
      entries.push({
        fullUrl: `http://cdss.local/fhir/Observation/${patientId}-obs-home-dbp`,
        resource: observation(patientId, encounterRef, 'home-dbp', '8462-4', homeBp[1], 'mmHg', 'mm[Hg]', 'home'),
      })
    }
  }
  bundle.entry = entries
  return bundle
}

export const htn = (): ConditionSpec => ({ key: 'htn', text: 'Primary hypertension', icd10: 'I10', snomed: '59621000' })
export const diabetes = (): ConditionSpec => ({ key: 'diabetes', text: 'Type 2 diabetes mellitus', icd10: 'E11', snomed: '44054006' })
export const ckd = (): ConditionSpec => ({ key: 'ckd', text: 'Chronic kidney disease', icd10: 'N18', snomed: '709044004' })
export const heartFailure = (): ConditionSpec => ({ key: 'heart-failure', text: 'Heart failure', icd10: 'I50.9', snomed: '84114007' })
export const cad = (): ConditionSpec => ({ key: 'cad', text: 'Atherosclerotic coronary artery disease', icd10: 'I25.0', snomed: '53741008' })

function conditionResource(patientId: string, condition: ConditionSpec): JsonObject {
  const coding: JsonObject[] = [{ system: ICD10, code: condition.icd10 }]
  if (condition.snomed) coding.push({ system: SNOMED, code: condition.snomed })
  return {
    resourceType: 'Condition',
    id: `${patientId}-cond-${condition.key}`,
    subject: { reference: `Patient/${patientId}` },
    code: { coding, text: condition.text },
  }
}

function observation(
  patientId: string,
  encounterRef: string,
  key: string,
  code: string,
  value: number,
  unit: string,
  ucumCode: string,
  role?: string,
): JsonObject {
  return {
    resourceType: 'Observation',
    id: `${patientId}-obs-${key}`,
    status: 'final',
    code: { coding: [{ system: LOINC, code }] },
    subject: { reference: `Patient/${patientId}` },
    encounter: { reference: encounterRef },
    ...(role ? { extension: [{ url: READING_ROLE, valueCode: role }] } : {}),
    valueQuantity: { value, unit, system: UCUM, code: ucumCode },
  }
}

function medicationRequest(patientId: string, encounterRef: string, medication: string): JsonObject {
  return {
    resourceType: 'MedicationRequest',
    id: `${patientId}-med-${medication.toLowerCase()}`,
    status: 'active',
    intent: 'order',
    medicationCodeableConcept: { text: medication },
    subject: { reference: `Patient/${patientId}` },
    encounter: { reference: encounterRef },
    authoredOn: '2026-01-15',
  }
}

function typedExtension(value: InputValue): JsonObject {
  if (typeof value === 'boolean') return { valueBoolean: value }
  if (typeof value === 'number') return { valueDecimal: value }
  return { valueString: value }
}
