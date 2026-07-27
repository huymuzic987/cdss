import type { TreeGraphNode, TreeSummary } from './api/types'

export interface ClinicalCode {
  symptomId: string
  nameVi: string
  nameEn: string
  icd10: string | null
  snomedCt: string | null
  loinc: string | null
  loincName: string | null
  decisionTreesVi: string[]
  decisionTreesEn: string[]
}

type CatalogRow = [
  string,
  string,
  string | null,
  string | null,
  string | null,
  string | null,
  string | null,
  string | null,
]

const rows: CatalogRow[] = [
  ['SYM0001', 'Tăng huyết áp', 'Hypertensive diseases', 'I10-I15', '38341003', null, 'Chẩn đoán THA, Phân tầng nguy cơ tim mạch, Ngưỡng và đích điều trị, Điều trị thiết yếu, Điều trị tối ưu, Phối hợp thuốc, THA người cao tuổi, THA + Đái Tháo Đường týp 2, THA + Bệnh mạch vành, THA + Suy tim, THA + Bệnh thận mạn, THA trong thai kỳ, THA kháng trị, THA cấp cứu', 'Hypertension Diagnosis, Risk Classification, Treatment Threshold and BP Target, Essential treatment strategy, Optimal treatment strategy, Drug Combination, Hypertension for the Elderly, Hypertension With Type 2 Diabetes, Hypertension + Coronary Artery Disease, Hypertension + Heart Failure, Hypertension With Chronic Kidney Disease, Hypertension in Pregnancy, Resistant Hypertension, Hypertensive Emergency'],
  ['SYM0002', 'Tăng huyết áp kháng trị', 'Resistant Hypertension', null, '845891000000103', null, 'Điều trị thiết yếu, Điều trị tối ưu, Phối hợp thuốc, THA kháng trị', 'Essential treatment strategy, Optimal treatment strategy, Drug Combination, Resistant Hypertension'],
  ['SYM0003', 'Tăng huyết áp cấp cứu', 'Hypertensive Emergency', null, '132721000119104', null, 'Chẩn đoán THA, THA cấp cứu', 'Hypertension Diagnosis, Hypertensive Emergency'],
  ['SYM0004', 'Tăng huyết áp khẩn cấp', 'Hypertensive Urgency', null, '443482000', null, 'THA cấp cứu', 'Hypertensive Emergency'],
  ['SYM0005', 'Tăng huyết áp trong thai kỳ', 'Gestational (pregnancy-induced) hypertension', 'O13', '48194001', null, 'THA trong thai kỳ, THA cấp cứu', 'Hypertension in Pregnancy, Hypertensive Emergency'],
  ['SYM0006', 'Tiền sản giật', 'Gestational [pregnancy-induced] hypertension with significant proteinuria', 'O14', '398254007', null, 'THA trong thai kỳ, THA cấp cứu', 'Hypertension in Pregnancy, Hypertensive Emergency'],
  ['SYM0007', 'Sản giật', 'Eclampsia', 'O15', '15938005', null, 'THA trong thai kỳ, THA cấp cứu', 'Hypertension in Pregnancy, Hypertensive Emergency'],
  ['SYM0008', 'Đái tháo đường týp 2', 'Type 2 Diabetes Mellitus', 'E11', '44054006', null, 'Ngưỡng và đích điều trị, THA + Đái Tháo Đường týp 2', 'Treatment Threshold and BP Target, Hypertension With Type 2 Diabetes'],
  ['SYM0009', 'Có bệnh tim mạch do xơ vữa', 'Atherosclerotic cardiovascular disease, so described', 'I25.0', '53741008', null, 'Ngưỡng và đích điều trị, THA + Bệnh mạch vành', 'Treatment Threshold and BP Target, Hypertension + Coronary Artery Disease'],
  ['SYM0010', 'Hội chứng mạch vành cấp', 'Acute Coronary Syndrome', null, '394659003', null, 'THA + Bệnh mạch vành, THA cấp cứu', 'Hypertension + Coronary Artery Disease, Hypertensive Emergency'],
  ['SYM0011', 'Nhồi máu cơ tim', 'Myocardial Infarction', 'I21.9', '22298006', null, 'THA + Bệnh mạch vành', 'Hypertension + Coronary Artery Disease'],
  ['SYM0012', 'Đau thắt ngực', 'Angina pectoris', 'I20', '194828000', null, 'Phối hợp thuốc, THA + Bệnh mạch vành', 'Drug Combination, Hypertension + Coronary Artery Disease'],
  ['SYM0013', 'Suy tim', 'Heart Failure', 'I50', '84114007', null, 'Ngưỡng và đích điều trị, Phối hợp thuốc, THA + Suy tim', 'Treatment Threshold and BP Target, Drug Combination, Hypertension + Heart Failure'],
  ['SYM0014', 'Bệnh thận mạn', 'Chronic Kidney Disease', 'N18', '709044004', null, 'Phân tầng nguy cơ tim mạch, Ngưỡng và đích điều trị, THA + Đái Tháo Đường týp 2, THA + Bệnh thận mạn, THA cấp cứu', 'Risk Classification, Treatment Threshold and BP Target, Hypertension With Type 2 Diabetes, Hypertension With Chronic Kidney Disease, Hypertensive Emergency'],
  ['SYM0015', 'Đột quỵ thiếu máu não', 'Acute Ischemic Stroke', 'I63', '422504002', null, 'THA cấp cứu', 'Hypertensive Emergency'],
  ['SYM0016', 'Cơn thiếu máu não thoáng qua', 'Transient Ischemic Attack', 'G45.9', '266257000', null, null, null],
  ['SYM0017', 'Rung nhĩ', 'Atrial fibrillation and atrial flutter, unspecified', 'I48.9', '49436004', null, 'Phối hợp thuốc', 'Drug Combination'],
  ['SYM0018', 'Phì đại thất trái', 'Left Ventricular Hypertrophy', 'I11.9', '55827005', null, 'THA + Suy tim, THA cấp cứu', 'Hypertension + Heart Failure, Hypertensive Emergency'],
  ['SYM0019', 'Suy tim phân suất tống máu bảo tồn', 'HFpEF', null, '446221000', '18043-0', 'THA + Suy tim', 'Hypertension + Heart Failure'],
  ['SYM0020', 'Suy tim phân suất tống máu giảm', 'HFrEF', null, '703272007', '18043-0', 'THA + Suy tim', 'Hypertension + Heart Failure'],
  ['SYM0021', 'Nhịp tim >80 lần/phút', 'Heart Rate >80 bpm', 'R00.0', null, '8867-4', 'Phân tầng nguy cơ tim mạch', 'Risk Classification'],
  ['SYM0022', 'Thừa cân', 'BMI ≥25 kg/m²', 'E66', '238131007', '39156-5', null, null],
  ['SYM0023', 'Béo phì', 'BMI ≥30 kg/m²', 'E66', '414916001', '39156-5', 'Phân tầng nguy cơ tim mạch', 'Risk Classification'],
  ['SYM0024', 'Creatinin máu tăng', 'Elevated Serum Creatinine', null, '166717003', '2160-0', 'THA + Bệnh thận mạn', 'Hypertension With Chronic Kidney Disease'],
  ['SYM0025', 'Albumin niệu', 'Albuminuria', 'R80', '274769005', '2709552', 'THA + Đái Tháo Đường týp 2, THA + Bệnh thận mạn', 'Hypertension With Type 2 Diabetes, Hypertension With Chronic Kidney Disease'],
  ['SYM0026', 'Protein niệu', 'Proteinuria', 'R80', '29738008', '2888-6', 'THA + Bệnh thận mạn', 'Hypertension With Chronic Kidney Disease'],
  ['SYM0027', 'LDL-C tăng', 'Elevated LDL Cholesterol', 'E78.0', '445445006', '69034', 'Phân tầng nguy cơ tim mạch', 'Risk Classification'],
  ['SYM0028', 'Triglycerid tăng', 'Hypertriglyceridemia', 'E78.1', '302870006', '2571-8', null, null],
  ['SYM0029', 'Đã ghép thận', 'History of Renal Transplant', null, '161665007', null, 'THA + Bệnh thận mạn', 'Hypertension With Chronic Kidney Disease'],
  ['SYM0030', 'Đang chạy thận nhân tạo', 'Maintenance Hemodialysis', 'Z99.2', '708931003', null, 'THA + Bệnh thận mạn', 'Hypertension With Chronic Kidney Disease'],
  ['SYM0031', 'Đã phẫu thuật bắc cầu động mạch vành', 'History of CABG', 'Z95.1', '232717009', null, 'THA + Bệnh mạch vành', 'Hypertension + Coronary Artery Disease'],
  ['SYM0032', 'Không tuân thủ điều trị', 'Medication Non-adherence', 'Z91.1', '702566000', '71799-1', 'THA + Đái Tháo Đường týp 2', 'Hypertension With Type 2 Diabetes'],
  ['SYM0033', 'Nam', 'Male', null, '248153007', '76689-9', 'Phân tầng nguy cơ tim mạch', 'Risk Classification'],
  ['SYM0034', 'Nữ', 'Female', null, '248152002', '76689-9', 'THA trong thai kỳ, THA cấp cứu', 'Hypertension in Pregnancy, Hypertensive Emergency'],
  ['SYM0035', 'Đang mang thai', 'Pregnancy', 'Z32', '77386006', '82810-3', 'Phối hợp thuốc, THA trong thai kỳ, THA cấp cứu', 'Drug Combination, Hypertension in Pregnancy, Hypertensive Emergency'],
  ['SYM0036', 'Sau sinh', 'Postpartum Period', 'Z39.0', '86569001', '96541-8', 'THA trong thai kỳ', 'Hypertension in Pregnancy'],
  ['SYM0037', 'Mãn kinh sớm', 'Premature Menopause', 'E28.3', '373717006', null, 'Phân tầng nguy cơ tim mạch', 'Risk Classification'],
  ['SYM0038', 'Người cao tuổi', 'Older Adult', null, null, null, 'Ngưỡng và đích điều trị, Điều trị thiết yếu, Điều trị tối ưu, THA người cao tuổi', 'Treatment Threshold and BP Target, Essential treatment strategy, Optimal treatment strategy, Hypertension for the Elderly'],
]

const splitList = (value: string | null) =>
  value?.split(',').map((item) => item.trim()).filter(Boolean) ?? []

export const clinicalCodeCatalog: ClinicalCode[] = rows.map(
  ([symptomId, nameVi, nameEn, icd10, snomedCt, loinc, decisionTreesVi, decisionTreesEn]) => ({
    symptomId,
    nameVi,
    nameEn: nameEn ?? '',
    icd10,
    snomedCt,
    loinc,
    loincName: null,
    decisionTreesVi: splitList(decisionTreesVi),
    decisionTreesEn: splitList(decisionTreesEn),
  }),
)

function normalize(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function phraseMatches(text: string, phrase: string): boolean {
  const normalizedPhrase = normalize(phrase)
  if (normalizedPhrase.length < 4) return false
  return ` ${normalize(text)} `.includes(` ${normalizedPhrase} `)
}

const treeKeyByCatalogName: Record<string, string> = {
  'hypertension diagnosis': 'hypertension-diagnosis',
  'risk classification': 'risk-classification',
  'treatment threshold and bp target': 'treatment-threshold-and-bp-target',
  'essential treatment strategy': 'essential-treatment-strategy',
  'optimal treatment strategy': 'optimal-treatment-strategy',
  'drug combination': 'drug-combination',
  'hypertension for the elderly': 'hypertension-older-adults',
  'hypertension with type 2 diabetes': 'hypertension-type-2-diabetes',
  'hypertension coronary artery disease': 'hypertension-coronary-artery-disease',
  'hypertension heart failure': 'hypertension-heart-failure',
  'hypertension with chronic kidney disease': 'hypertension-chronic-kidney-disease',
  'hypertension in pregnancy': 'hypertension-in-pregnancy',
  'resistant hypertension': 'resistant-hypertension',
  'hypertensive emergency': 'hypertensive-emergency',
}

function belongsToTree(code: ClinicalCode, tree: TreeSummary): boolean {
  if (code.decisionTreesEn.length === 0 && code.decisionTreesVi.length === 0) return true
  return (
    code.decisionTreesEn.some((name) => treeKeyByCatalogName[normalize(name)] === tree.tree_key) ||
    code.decisionTreesEn.some((name) => normalize(name) === normalize(tree.name_en)) ||
    code.decisionTreesVi.some((name) => normalize(name) === normalize(tree.name_vi))
  )
}

export function getClinicalCodesForNode(
  node: TreeGraphNode,
  tree: TreeSummary,
): ClinicalCode[] {
  const searchableText = `${node.text_en} ${node.text_vi}`
  return clinicalCodeCatalog.filter(
    (code) =>
      belongsToTree(code, tree) &&
      (phraseMatches(searchableText, code.nameEn) || phraseMatches(searchableText, code.nameVi)),
  )
}

export function clinicalCodesToText(codes: ClinicalCode[]): string {
  return codes
    .map((code) => {
      const values = [
        code.icd10 && `ICD-10: ${code.icd10}`,
        code.snomedCt && `SNOMED CT: ${code.snomedCt}`,
        code.loinc && `LOINC: ${code.loinc}`,
      ].filter(Boolean)
      return `${code.nameEn || code.nameVi}\n${values.join('\n')}`
    })
    .join('\n\n')
}
