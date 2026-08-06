/** Materialize the current patient-preset catalog as canonical FHIR R4 JSON. */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const seedPath = path.join(root, 'backups', 'seed.sql')
const outputRoot = path.join(root, 'data', 'fhir')
const frontendCatalogPath = path.join(
  root,
  'frontend',
  'src',
  'panels',
  'patientPresets',
  'presets.generated.json',
)

const SNOMED_SYSTEM = 'http://snomed.info/sct'
const ICD10_SYSTEM = 'http://hl7.org/fhir/sid/icd-10'
const PRESET_META_BASE = 'http://cdss.local/fhir/CodeSystem/preset'
const CLINICAL_FLAG_SYSTEM = 'http://cdss.local/fhir/CodeSystem/clinical-flag'
const BASE_URL = 'http://example.org/fhir'

const { LEGACY_PATIENT_PRESETS: PATIENT_PRESETS } = await import('./legacyPatientPresets.ts')
const tables = parseReferenceTables(fs.readFileSync(seedPath, 'utf8'))
const allowedSnomed = new Set([
  ...tables.symptoms.map((row) => row.snomed_code),
  ...tables.contraindication_drugs.map((row) => row.snomedct_2026_06_01),
  ...tables.medicines.map((row) => row.snomed_code),
].filter(Boolean))

if (allowedSnomed.size === 0) {
  throw new Error('Reference catalogs contain no SNOMED CT codes; refusing to generate presets')
}

const generated = PATIENT_PRESETS.map((preset) => {
  const bundle = enrichBundle(deepClone(preset.bundle), preset)
  validateBundle(bundle, allowedSnomed, preset.id)
  return bundle
})

const counts = new Map()
const outputDirectories = new Set()
for (const bundle of generated) {
  const metadata = metadataFromBundle(bundle)
  const directory = path.join(outputRoot, directoryName(metadata.category))
  outputDirectories.add(directory)
  if (!counts.has(directory)) {
    counts.set(directory, 0)
    fs.mkdirSync(directory, { recursive: true })
    for (const entry of fs.readdirSync(directory)) {
      if (entry.endsWith('.json')) fs.rmSync(path.join(directory, entry), { force: true })
    }
  }
  const index = counts.get(directory) + 1
  counts.set(directory, index)
  const filename = `${String(index).padStart(3, '0')}-${safeFilename(metadata.id)}.json`
  fs.writeFileSync(path.join(directory, filename), `${JSON.stringify(bundle, null, 2)}\n`, 'utf8')
}

fs.writeFileSync(frontendCatalogPath, `${JSON.stringify(generated, null, 2)}\n`, 'utf8')
console.log(`Generated ${generated.length} FHIR R4 patient presets`)
console.log(`Allowed SNOMED CT codes from reference catalogs: ${allowedSnomed.size}`)
console.log(`Output directories: ${outputDirectories.size}`)

function enrichBundle(bundle, preset) {
  const entries = Array.isArray(bundle.entry) ? bundle.entry : []
  const resources = entries.map((entry) => entry?.resource).filter((resource) => resource && typeof resource === 'object')
  const patient = resources.find((resource) => resource.resourceType === 'Patient')
  if (!patient) throw new Error(`Preset ${preset.id} has no Patient resource`)

  bundle.id = normalizeFhirId(`bundle-${preset.id}`)
  bundle.type = 'collection'
  bundle.identifier = { system: `${PRESET_META_BASE}/id`, value: preset.id }
  bundle.meta = { ...(bundle.meta ?? {}), tag: [
    { system: `${PRESET_META_BASE}/category`, code: preset.category, display: preset.category },
    { system: `${PRESET_META_BASE}/label`, code: preset.id, display: preset.label },
    { system: `${PRESET_META_BASE}/description`, code: preset.id, display: preset.description },
    { system: `${PRESET_META_BASE}/snomed-source`, code: 'database-reference-catalog', display: 'SNOMED CT sourced from reference tables' },
    ...((bundle.meta?.tag ?? []).filter((tag) => !String(tag?.system).startsWith(`${PRESET_META_BASE}/`))),
  ] }

  normalizeResourceIds(entries)
  for (const entry of entries) {
    const resource = entry?.resource
    if (resource?.resourceType && resource?.id) {
      entry.fullUrl = `${BASE_URL}/${resource.resourceType}/${resource.id}`
    }
  }

  for (const resource of resources) {
    if (resource.resourceType !== 'Condition') continue
    const coding = Array.isArray(resource.code?.coding) ? resource.code.coding : []
    const icd10 = coding.find((item) => item?.system === ICD10_SYSTEM)?.code
    const localFlag = coding.find((item) => item?.system === CLINICAL_FLAG_SYSTEM)?.code
    resource.code.coding = coding.filter((item) => item?.system !== SNOMED_SYSTEM || allowedSnomed.has(item.code))
    const match = findReferenceCondition(localFlag, icd10)
    if (match?.snomed_code && !resource.code.coding.some((item) => item?.system === SNOMED_SYSTEM && item.code === match.snomed_code)) {
      resource.code.coding.push({ system: SNOMED_SYSTEM, code: match.snomed_code, display: match.name_en ?? match.disease_finding_eng })
    }
  }

  for (const resource of resources) {
    if (resource.resourceType !== 'MedicationRequest') continue
    const concept = resource.medicationCodeableConcept ?? {}
    const coding = Array.isArray(concept.coding) ? concept.coding : []
    const name = String(concept.text ?? '').trim()
    const medicine = tables.medicines.find((row) => row.name && row.name.toLowerCase() === name.toLowerCase())
    // The current medicines seed has nullable SNOMED values. Omit the coding
    // when the table has no value; never invent a medication code.
    if (medicine?.snomed_code && !coding.some((item) => item?.system === SNOMED_SYSTEM && item.code === medicine.snomed_code)) {
      concept.coding = [...coding, { system: SNOMED_SYSTEM, code: medicine.snomed_code, display: medicine.name }]
      resource.medicationCodeableConcept = concept
    }
  }
  return bundle
}

function normalizeResourceIds(entries) {
  const idMap = new Map()
  for (const entry of entries) {
    const resource = entry?.resource
    if (!resource?.id) continue
    const originalId = String(resource.id)
    const normalizedId = normalizeFhirId(originalId)
    idMap.set(originalId, normalizedId)
    resource.id = normalizedId
  }
  for (const entry of entries) rewriteReferences(entry, idMap)
}

function normalizeFhirId(value) {
  return String(value).replace(/[^A-Za-z0-9.-]/g, '-').slice(0, 64) || 'resource'
}

function rewriteReferences(value, idMap) {
  if (Array.isArray(value)) {
    for (const item of value) rewriteReferences(item, idMap)
    return
  }
  if (!value || typeof value !== 'object') return
  if (typeof value.reference === 'string') {
    const slash = value.reference.indexOf('/')
    if (slash > 0) {
      const resourceType = value.reference.slice(0, slash)
      const resourceId = value.reference.slice(slash + 1)
      if (idMap.has(resourceId)) value.reference = `${resourceType}/${idMap.get(resourceId)}`
    }
  }
  for (const child of Object.values(value)) rewriteReferences(child, idMap)
}

function findReferenceCondition(localFlag, icd10) {
  const aliases = {
    has_type_2_diabetes: ['diabetes'], has_diabetes: ['diabetes'],
    has_ckd: ['chronic kidney disease'], has_ckd_stage_3_or_higher: ['chronic kidney disease'],
    has_heart_failure: ['heart failure'], has_coronary_artery_disease: ['coronary artery disease'],
    has_cardiovascular_disease: ['cardiovascular disease'], has_stroke: ['stroke'],
    has_tia: ['transient ischemic attack', 'tia'], is_pregnant: ['pregnancy'], is_postpartum: ['postpartum'],
  }
  const terms = aliases[localFlag] ?? []
  const symptom = tables.symptoms.find((row) => {
    if (!row.snomed_code) return false
    if (icd10 && row.icd10_code === icd10) return true
    const text = `${row.name_en ?? ''} ${row.description_en ?? ''}`.toLowerCase()
    return terms.some((term) => text.includes(term))
  })
  if (symptom) return symptom
  return tables.contraindication_drugs.find((row) => row.snomedct_2026_06_01 && icd10 && row.icd10_vn_1_decimal === icd10)
}

function validateBundle(bundle, allowed, presetId) {
  if (bundle.resourceType !== 'Bundle' || bundle.type !== 'collection') throw new Error(`${presetId} is not a FHIR R4 collection Bundle`)
  const patients = (bundle.entry ?? []).filter((entry) => entry?.resource?.resourceType === 'Patient')
  if (patients.length !== 1) throw new Error(`${presetId} must contain exactly one Patient`)
  for (const entry of bundle.entry ?? []) {
    const resource = entry?.resource
    if (!resource?.resourceType || !resource?.id) throw new Error(`${presetId} has an invalid Bundle entry`)
    if (!/^[A-Za-z0-9.-]{1,64}$/.test(resource.id)) throw new Error(`${presetId} has an invalid FHIR resource id ${resource.id}`)
    for (const coding of codingsIn(resource)) {
      if (coding.system === SNOMED_SYSTEM && !allowed.has(coding.code)) throw new Error(`${presetId} contains unknown SNOMED CT code ${coding.code}`)
    }
  }
}

function codingsIn(resource) {
  if (resource?.resourceType === 'Condition') return resource.code?.coding ?? []
  if (resource?.resourceType === 'MedicationRequest') return resource.medicationCodeableConcept?.coding ?? []
  return []
}

function metadataFromBundle(bundle) {
  const tag = (name) => (bundle.meta?.tag ?? []).find((item) => item?.system === `${PRESET_META_BASE}/${name}`)
  return { id: String(bundle.identifier?.value ?? bundle.id), category: String(tag('category')?.display ?? 'Generated Patient Presets') }
}

function directoryName(category) {
  return {
    'Diagnosis Routes': 'htn_presets',
    'Demographic & Comorbidity Diversity': 'comorbidity_presets',
    'Follow-Up Visits': 'follow_up_presets',
    'Modifier & Complication Trees': 'modifier_presets',
    'Drug Contraindication Tests': 'contraindication_presets',
    'Pregnancy & Postpartum': 'pregnancy_presets',
    'Pregnancy Follow-Up Sequence': 'pregnancy_follow_up_presets',
  }[category] ?? 'other_presets'
}

function safeFilename(value) { return value.replace(/[^A-Za-z0-9._-]+/g, '-') }

function parseReferenceTables(sql) {
  return { medicines: parseInserts(sql, 'medicines'), symptoms: parseInserts(sql, 'symptoms'), contraindication_drugs: parseInserts(sql, 'contraindication_drugs') }
}

function parseInserts(sql, table) {
  const rows = []
  const pattern = new RegExp(`INSERT INTO public\\.${table}\\s*\\(([^)]*)\\)\\s*VALUES\\s*\\(([\\s\\S]*?)\\)\\s*ON CONFLICT`, 'gi')
  for (const match of sql.matchAll(pattern)) {
    const columns = match[1].split(',').map((item) => item.trim())
    const values = splitSqlValues(match[2]).map(parseSqlValue)
    rows.push(Object.fromEntries(columns.map((column, index) => [column, values[index] ?? null])))
  }
  return rows
}

function splitSqlValues(value) {
  const result = []; let current = ''; let quoted = false
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index]
    if (char === "'") {
      current += char
      if (quoted && value[index + 1] === "'") { current += value[index + 1]; index += 1 } else quoted = !quoted
    } else if (char === ',' && !quoted) { result.push(current.trim()); current = '' } else current += char
  }
  result.push(current.trim()); return result
}

function parseSqlValue(value) {
  if (value === 'NULL') return null
  if (value === 'TRUE') return true
  if (value === 'FALSE') return false
  if (value.startsWith("'") && value.endsWith("'")) return value.slice(1, -1).replaceAll("''", "'")
  return value
}

function deepClone(value) { return JSON.parse(JSON.stringify(value)) }
