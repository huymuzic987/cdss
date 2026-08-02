import type { EvaluationResponse, JsonObject, TreeGraphResponse } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { ImportantPathStep } from './criticalSummaryTypes'

export function deriveAlertTitle(
  log: EvaluationResponse['traversal_log'],
  graphs: Record<string, TreeGraphResponse>,
  path: ImportantPathStep[],
  input: JsonObject,
  locale: ClinicalDecisionSupportLocale,
): string {
  return significantClinicalTitle(input, path, locale)
    ?? linkedDiseaseTitle(log, graphs, locale)
    ?? (locale === 'vi' ? 'Tăng huyết áp' : 'Hypertension')
}

export function titleContainsFinding(title: string, finding: string): boolean {
  if (isRoutineAlertFinding(finding)) return true
  if (/\b(?:high[- ]normal|normal|grade\s*[1-3]|isolated systolic)\s+(?:blood pressure|bp)\b/i.test(finding)) {
    return true
  }
  const normalizedTitle = title.toLocaleLowerCase()
  const normalizedFinding = finding.toLocaleLowerCase()
  return normalizedTitle.includes(normalizedFinding) || normalizedFinding.includes(normalizedTitle)
}

export function isHypertensionLabel(label: string): boolean {
  return /hypertension|tăng huyết áp/i.test(label)
}

function linkedDiseaseTitle(
  log: EvaluationResponse['traversal_log'],
  graphs: Record<string, TreeGraphResponse>,
  locale: ClinicalDecisionSupportLocale,
): string | undefined {
  const links = log.filter((entry) => entry.event === 'node_entered' && entry.node_type === 'LINK')
  const routeTokens = links.map((entry) => {
    const node = graphs[entry.tree_key]?.nodes.find((candidate) => candidate.node_key === entry.node_key)
    return `${entry.tree_key} ${entry.node_key} ${node?.link_target_tree_key ?? ''}`.toUpperCase()
  })
  const allTokens = `${routeTokens.join(' ')} ${log.map((entry) => entry.tree_key).join(' ')}`.toUpperCase()
  const routes: Array<[RegExp, string, string]> = [
    [/HYPERTENSIVE[_-]EMERGENCY/, 'Hypertensive emergency', 'Cấp cứu tăng huyết áp'],
    [/HYPERTENSION[_-]IN[_-]PREGNANCY/, 'Hypertension in pregnancy', 'Tăng huyết áp trong thai kỳ'],
    [/RESISTANT[_-]HYPERTENSION/, 'Resistant hypertension', 'Tăng huyết áp kháng trị'],
    [/HYPERTENSION[_-]HEART[_-]FAILURE|HEART[_-]FAILURE[_-]MODIFIER/, 'Heart failure', 'Suy tim'],
    [/HYPERTENSION[_-]CORONARY[_-]ARTERY[_-]DISEASE|CORONARY[_-]ARTERY[_-]DISEASE[_-]MODIFIER/, 'Coronary artery disease', 'Bệnh động mạch vành'],
    [/HYPERTENSION[_-]TYPE[_-]2[_-]DIABETES|TYPE[_-]2[_-]DIABETES[_-]MODIFIER/, 'Type 2 diabetes', 'Đái tháo đường típ 2'],
    [/HYPERTENSION[_-]CHRONIC[_-]KIDNEY[_-]DISEASE|CHRONIC[_-]KIDNEY[_-]DISEASE[_-]MODIFIER/, 'Chronic kidney disease', 'Bệnh thận mạn'],
  ]
  const matched = routes.find(([pattern]) => pattern.test(allTokens))
  return matched ? (locale === 'vi' ? matched[2] : matched[1]) : undefined
}

function significantClinicalTitle(
  input: JsonObject,
  path: ImportantPathStep[],
  locale: ClinicalDecisionSupportLocale,
): string | undefined {
  const vi = locale === 'vi'
  const pathText = path.map((step) => `${step.label} ${step.detail ?? ''}`).join(' ')
  if (/\bHELLP\b/i.test(pathText)) return vi ? 'Hội chứng HELLP' : 'HELLP syndrome'
  if (/\bECLAMPSIA\b/i.test(pathText)) return vi ? 'Sản giật' : 'Eclampsia'
  if (/\bPREECLAMPSIA\b/i.test(pathText)) return vi ? 'Tiền sản giật' : 'Preeclampsia'
  const acuteConditions: Array<[string, string, string]> = [
    ['has_hypertensive_encephalopathy', 'Hypertensive encephalopathy', 'Bệnh não do tăng huyết áp'],
    ['has_acute_ischemic_stroke', 'Acute ischemic stroke', 'Đột quỵ thiếu máu não cấp'],
    ['has_acute_intracerebral_hemorrhage', 'Acute intracerebral hemorrhage', 'Xuất huyết não cấp'],
    ['has_acute_coronary_syndrome', 'Acute coronary syndrome', 'Hội chứng vành cấp'],
    ['has_acute_cardiogenic_pulmonary_edema', 'Cardiogenic pulmonary edema', 'Phù phổi cấp do tim'],
    ['has_acute_aortic_syndrome', 'Acute aortic syndrome', 'Hội chứng động mạch chủ cấp'],
    ['has_eclampsia_severe_preeclampsia_or_hellp', 'Eclampsia / severe preeclampsia / HELLP', 'Sản giật / tiền sản giật nặng / HELLP'],
    ['has_tma_or_acute_kidney_injury', 'TMA / acute kidney injury', 'TMA / tổn thương thận cấp'],
  ]
  const acute = acuteConditions
    .filter(([key]) => input[key] === true)
    .map(([, en, viLabel]) => vi ? viLabel : en)
  if (acute.length > 0) return acute.slice(0, 2).join(' · ')
  if (input.has_target_organ_damage === true) {
    return vi ? 'Tổn thương cơ quan đích cấp' : 'Acute target-organ damage'
  }
  const conditions: string[] = []
  if (input.has_high_preeclampsia_risk === true) conditions.push(vi ? 'Tiền sản giật' : 'Preeclampsia')
  const diseaseFlags: Array<[string[], string, string]> = [
    [['has_type_2_diabetes', 'has_diabetes'], 'Type 2 diabetes', 'Đái tháo đường típ 2'],
    [['has_ckd', 'has_ckd_stage_3_or_higher'], 'Chronic kidney disease', 'Bệnh thận mạn'],
    [['has_coronary_artery_disease'], 'Coronary artery disease', 'Bệnh động mạch vành'],
    [['has_heart_failure'], 'Heart failure', 'Suy tim'],
  ]
  for (const [keys, en, viLabel] of diseaseFlags) {
    if (keys.some((key) => input[key] === true)) conditions.push(vi ? viLabel : en)
  }
  return conditions.length > 0 ? conditions.slice(0, 2).join(' · ') : undefined
}

function isRoutineAlertFinding(label: string): boolean {
  return /hypertension class|clinic bp|risk level|hypertension|tăng huyết áp/i.test(label)
}
