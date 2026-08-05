import { formToPayload } from '../mockPatientForm/payload'
import { DEFAULT_FORM } from '../mockPatientForm/types'
import { diagnosisPresets } from './diagnosis'
import { followUpPresets } from './followUp'
import { cardioModifierPresets } from './modifiersCardio'
import { renalModifierPresets } from './modifiersRenal'
import {
  augmentWorkingBundle,
  cad,
  ckd,
  diabetes,
  heartFailure,
  htn,
  type ConditionSpec,
  type InputValue,
  type LabSpec,
} from './contraindicationSupport'
import type { PatientPresetDefinition } from './shared'
import type { JsonObject } from '../../api/types'

interface ContraindicationCaseSpec {
  id: string
  label: string
  description: string
  sourceId: string
  conditions: ConditionSpec[]
  medications: string[]
  inputs?: Record<string, InputValue>
  homeBp?: [number, number]
  labs?: LabSpec[]
}

const finding = (key: string, text: string, icd10: string, snomed?: string): ConditionSpec => ({ key, text, icd10, snomed })

const workingDefinitions: PatientPresetDefinition[] = [
  ...diagnosisPresets,
  ...followUpPresets,
  ...cardioModifierPresets,
  ...renalModifierPresets,
]

const workingDefinitionById = new Map(workingDefinitions.map((definition) => [definition.id, definition]))

const pregnancyInputs: Record<string, InputValue> = {
  pregnancy_status: true,
  is_pregnant: true,
  has_hypertension_after_week_20: true,
  weeks_persisting_postpartum: 0,
}

const cases: ContraindicationCaseSpec[] = [
  {
    id: 'contra-01-gout-thiazide', label: '01 — Gout removes thiazide subgroups', sourceId: 'stage2-htn',
    description: 'Copied from the existing Stage 2 Hypertension preset; gout must remove only the contraindicated thiazide subgroups from D.',
    conditions: [htn(), finding('gout', 'Gout', 'M10.9', '90560007'), diabetes(), finding('metabolic', 'Metabolic syndrome', 'E88.8', '237602007')],
    inputs: { gout_status: true, metabolic_syndrome: true }, medications: ['CHLORTHALIDONE', 'BISOPROLOL'],
  },
  {
    id: 'contra-02-glucose-intolerance', label: '02 — Glucose intolerance flags thiazide subgroups', sourceId: 'stage1-htn',
    description: 'Copied from the existing Stage 1 Hypertension preset; relative thiazide findings remain selectable for review.',
    conditions: [htn(), finding('glucose', 'Impaired glucose tolerance', 'R73.0', '9414007'), diabetes(), ckd()],
    inputs: { glucose_intolerance: true }, medications: ['CHLORTHALIDONE', 'BISOPROLOL'],
  },
  {
    id: 'contra-03-pregnancy-thiazide', label: '03 — Pregnancy flags thiazide subgroups', sourceId: 'stage2-htn',
    description: 'Copied from the existing Stage 2 Hypertension preset; relative thiazide findings remain selectable for review.',
    conditions: [htn(), finding('pregnancy', 'Pregnancy', 'Z32', '77386006'), diabetes()],
    inputs: pregnancyInputs, medications: ['CHLORTHALIDONE'], homeBp: [130, 80],
  },
  {
    id: 'contra-04-pregnancy-ace', label: '04 — Pregnancy removes ACE inhibitor', sourceId: 'ckd-modifier',
    description: 'Copied from the existing CKD modifier preset; pregnancy must remove the ACE inhibitor class.',
    conditions: [htn(), finding('pregnancy', 'Pregnancy', 'Z32', '77386006'), ckd()],
    inputs: pregnancyInputs, medications: ['ENALAPRIL'], homeBp: [136, 84],
  },
  {
    id: 'contra-05-pregnancy-arb', label: '05 — Pregnancy removes ARB', sourceId: 'cad-revascularization',
    description: 'Copied from the existing CAD revascularization preset; pregnancy must remove the ARB class.',
    conditions: [htn(), finding('pregnancy', 'Pregnancy', 'Z32', '77386006'), cad()],
    inputs: pregnancyInputs, medications: ['CANDESARTAN'], homeBp: [132, 80],
  },
  {
    id: 'contra-06-pregnancy-aliskiren', label: '06 — Pregnancy removes aliskiren', sourceId: 'ckd-modifier',
    description: 'Copied from the existing CKD modifier preset; pregnancy must remove the direct renin inhibitor.',
    conditions: [htn(), finding('pregnancy', 'Pregnancy', 'Z32', '77386006'), ckd()],
    inputs: pregnancyInputs, medications: ['ALISKIREN'], homeBp: [134, 82],
  },
  {
    id: 'contra-07-hypercalcaemia-thiazide', label: '07 — Hypercalcaemia flags thiazide subgroups', sourceId: 'stage2-htn',
    description: 'Copied from the existing Stage 2 Hypertension preset; relative thiazide findings remain selectable for review.',
    conditions: [htn(), finding('hypercalcaemia', 'Hypercalcaemia', 'E83.5', '66931009'), ckd()],
    inputs: { hypercalcaemia: true }, medications: ['INDAPAMIDE'],
  },
  {
    id: 'contra-08-hypokalaemia-thiazide', label: '08 — Hypokalaemia flags thiazide subgroups', sourceId: 'ckd-modifier',
    description: 'Copied from the existing CKD modifier preset; relative thiazide findings remain selectable for review.',
    conditions: [htn(), finding('hypokalaemia', 'Hypokalemia', 'E87.6', '43339004'), diabetes(), ckd()],
    inputs: { hypokalaemia: true }, medications: ['CHLORTHALIDONE'],
    labs: [{ key: 'potassium', code: '6298-4', value: 3.1, unit: 'mmol/L', ucumCode: 'mmol/L' }],
  },
  {
    id: 'contra-09-asthma-beta', label: '09 — Asthma removes beta blocker', sourceId: 'type2-diabetes-modifier',
    description: 'Copied from the existing type 2 diabetes modifier preset with active asthma.',
    conditions: [htn(), finding('asthma', 'Asthma', 'J45.9', '195967001'), diabetes()],
    inputs: { asthma_severity: 'moderate persistent' }, medications: ['BISOPROLOL'],
  },
  {
    id: 'contra-10-sinoatrial-block', label: '10 — Sinoatrial block removes beta and non-DHP CCB', sourceId: 'cad-revascularization',
    description: 'Copied from the existing CAD revascularization preset with sinoatrial block.',
    conditions: [htn(), finding('sinoatrial-block', 'Sinoatrial block', 'I45.5', '65778007'), cad()],
    medications: ['BISOPROLOL', 'DILTIAZEM'],
  },
  {
    id: 'contra-11-av-block', label: '11 — High-grade AV block removes beta and non-DHP CCB', sourceId: 'heart-failure-hfmref',
    description: 'Copied from the existing heart-failure modifier preset with high-grade AV block.',
    conditions: [htn(), finding('av-block', 'High-grade atrioventricular block', 'I44.1', '28189009'), heartFailure()],
    inputs: { AV_block_grade: 'high-grade' }, medications: ['BISOPROLOL', 'VERAPAMIL'],
  },
  {
    id: 'contra-12-bradycardia', label: '12 — Bradycardia removes beta and non-DHP CCB', sourceId: 'heart-failure-hfpef',
    description: 'Copied from the existing heart-failure modifier preset with a documented low heart rate.',
    conditions: [htn(), finding('bradycardia', 'Bradycardia', 'R00.1', '48867003'), ckd(), heartFailure()],
    inputs: { heart_rate: 52 }, medications: ['BISOPROLOL', 'DILTIAZEM'],
    labs: [{ key: 'heart-rate', code: '8867-4', value: 52, unit: 'beats/min', ucumCode: '/min' }],
  },
  {
    id: 'contra-13-athlete-beta', label: '13 — Athlete flags beta blocker', sourceId: 'stage1-htn',
    description: 'Copied from the existing Stage 1 Hypertension preset; the relative beta-blocker finding remains selectable for review.',
    conditions: [htn(), finding('athlete', 'Athlete examination', 'Z02.5'), diabetes()],
    inputs: { athlete_status: true }, medications: ['BISOPROLOL'],
  },
  {
    id: 'contra-14-tachycardia-dhp', label: '14 — Tachycardia flags DHP CCB', sourceId: 'cad-revascularization',
    description: 'Copied from the existing CAD revascularization preset; the relative DHP finding remains selectable for review.',
    conditions: [htn(), finding('tachycardia', 'Tachycardia', 'R00.0', '3424008'), cad()],
    inputs: { heart_rate: 112 }, medications: ['NIFEDIPINE'],
    labs: [{ key: 'heart-rate', code: '8867-4', value: 112, unit: 'beats/min', ucumCode: '/min' }],
  },
  {
    id: 'contra-15-hfref-dhp', label: '15 — HFrEF flags DHP CCB', sourceId: 'heart-failure-hfmref',
    description: 'Copied from the existing HFmrEF modifier preset; the relative DHP finding remains selectable for review.',
    conditions: [htn(), finding('hfrEF', 'Heart failure with reduced EF, NYHA class III', 'I50.2', '417996009'), ckd()],
    inputs: { heart_failure_reduced_ef_nyha_3_or_4: true, NYHA_class: 'III' }, medications: ['NIFEDIPINE'],
    labs: [{ key: 'lvef', code: '10230-1', value: 32, unit: '%', ucumCode: '%' }],
  },
  {
    id: 'contra-16-leg-oedema-dhp', label: '16 — Severe leg oedema flags DHP CCB', sourceId: 'heart-failure-hfpef',
    description: 'Copied from the existing HFpEF modifier preset; the relative DHP finding remains selectable for review.',
    conditions: [htn(), finding('leg-oedema', 'History of severe leg oedema', 'R60.0', '271809000'), heartFailure(), ckd()],
    inputs: { severe_leg_edema_history: true }, medications: ['AMLODIPINE'],
  },
  {
    id: 'contra-17-lv-dysfunction', label: '17 — LV systolic dysfunction removes non-DHP CCB', sourceId: 'type2-diabetes-modifier',
    description: 'Copied from the existing type 2 diabetes modifier preset with reduced LV systolic function.',
    conditions: [htn(), finding('lv-systolic', 'Left ventricular systolic dysfunction', 'I51.9', '134401001'), cad(), diabetes()],
    inputs: { LVEF: 35 }, medications: ['DILTIAZEM'],
    labs: [{ key: 'lvef', code: '10230-1', value: 35, unit: '%', ucumCode: '%' }],
  },
  {
    id: 'contra-18-constipation', label: '18 — Constipation flags non-DHP CCB', sourceId: 'type2-diabetes-no-cv-risk-maintain',
    description: 'Copied from the existing type 2 diabetes no-CV-risk preset; the relative non-DHP finding remains selectable for review.',
    conditions: [htn(), finding('constipation', 'Constipation', 'K59.0', '14760008'), diabetes()],
    inputs: { constipation: true }, medications: ['VERAPAMIL'],
  },
  {
    id: 'contra-19-angioedema-ace', label: '19 — Angioedema removes ACE inhibitor', sourceId: 'ckd-modifier',
    description: 'Copied from the existing CKD modifier preset with a history of angioedema.',
    conditions: [htn(), finding('angioedema', 'History of angioedema', 'T78.3', '41291007'), diabetes()],
    inputs: { angioedema_history: true }, medications: ['ENALAPRIL'],
  },
  {
    id: 'contra-20-poly-risk-ras', label: '20 — Poly-risk case removes RAS/MRA classes', sourceId: 'med-followup-resistant',
    description: 'Copied from the existing resistant-hypertension follow-up preset with CKD, hyperkalaemia, AKI, renal artery stenosis, and no contraception.',
    conditions: [
      htn(), diabetes(), heartFailure(),
      finding('ckd4', 'Chronic kidney disease stage 4', 'N18.4', '431857002'),
      finding('hyperkalaemia', 'Hyperkalemia', 'E87.5', '14140009'),
      finding('renal-stenosis', 'Bilateral renal artery stenosis', 'I70.1', '425414000'),
      finding('aki', 'Acute kidney injury', 'N17.9', '14669001'),
      finding('contraception', 'Woman of childbearing potential not using contraception', 'Z30.9'),
    ],
    inputs: { renal_artery_stenosis: true, acute_kidney_injury: true, woman_of_childbearing_potential_not_using_contraception: true },
    medications: ['ENALAPRIL', 'CANDESARTAN', 'EPLERENONE'],
    labs: [
      { key: 'eGFR', code: '98979-8', value: 24, unit: 'mL/min', ucumCode: 'mL/min' },
      { key: 'potassium', code: '6298-4', value: 6.2, unit: 'mmol/L', ucumCode: 'mmol/L' },
    ],
  },
]

function buildCaseBundle(caseData: ContraindicationCaseSpec): JsonObject {
  const source = workingDefinitionById.get(caseData.sourceId)
  if (!source || !('data' in source)) {
    throw new Error(`Contraindication preset source must be a form preset: ${caseData.sourceId}`)
  }
  const bundle = formToPayload({ ...DEFAULT_FORM, ...source.data }, caseData.id)
  return augmentWorkingBundle(bundle, caseData.id, caseData)
}

export const contraindicationCases = cases.map((caseData) => ({
  ...caseData,
  bundle: buildCaseBundle(caseData),
}))
