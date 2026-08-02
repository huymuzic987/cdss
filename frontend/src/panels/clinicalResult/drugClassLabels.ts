import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

const CLASS_NAMES: Record<string, [string, string]> = {
  A: ['RAS inhibitors', 'Ức chế hệ RAS'],
  B: ['Beta blockers', 'Chẹn beta'],
  C: ['Calcium channel blockers', 'Chẹn kênh canxi'],
  D: ['Diuretics', 'Lợi tiểu'],
}

const SUBGROUP_NAMES: Array<[RegExp, string, string]> = [
  [/\bACEI?\b|ACE inhibitor/i, 'ACE inhibitor', 'Ức chế men chuyển (ƯCMC)'],
  [/\bARB\b|Angiotensin II receptor/i, 'Angiotensin II receptor blocker', 'Chẹn thụ thể Angiotensin II (CTTA)'],
  [/\bARNI\b|neprilysin/i, 'Angiotensin receptor–neprilysin inhibitor (ARNI)', 'Chẹn thụ thể Angiotensin–neprilysin (ARNI)'],
  [/\bbeta\b|\bCB\b/i, 'Beta blocker', 'Chẹn beta (CB)'],
  [/non[- ]?DHP|non[- ]?dihydropyridine/i, 'Non-dihydropyridine', 'Nhóm non-dihydropyridine'],
  [/\bDHP\b|dihydropyridine/i, 'Dihydropyridine', 'Nhóm dihydropyridine'],
  [/\bMRA\b|mineralocorticoid/i, 'Mineralocorticoid receptor antagonist (potassium-sparing)', 'Đối kháng thụ thể mineralocorticoid (lợi tiểu giữ kali)'],
  [/alpha-?2|Chủ vận chọn lọc alpha-2/i, 'Centrally acting antihypertensive', 'Thuốc hạ áp tác động trung ương'],
  [/Giảm Adrenergic/i, 'Peripheral adrenergic inhibitor', 'Thuốc giảm adrenergic ngoại biên'],
  [/Giãn mạch/i, 'Direct vasodilator', 'Thuốc giãn mạch trực tiếp'],
  [/Alpha giao cảm/i, 'Alpha blocker', 'Thuốc chẹn alpha'],
  [/Renin trực tiếp/i, 'Direct renin inhibitor', 'Thuốc ức chế renin trực tiếp'],
]

export function drugClassDisplay(
  code: string,
  fallback: string,
  locale: ClinicalDecisionSupportLocale,
): string {
  const names = CLASS_NAMES[code.toUpperCase()]
  return names ? `${code.toUpperCase()} · ${names[locale === 'vi' ? 1 : 0]}` : fallback
}

export function drugSubgroupDisplay(
  subgroup: string | undefined,
  locale: ClinicalDecisionSupportLocale,
): string | undefined {
  if (!subgroup) return undefined
  const match = SUBGROUP_NAMES.find(([pattern]) => pattern.test(subgroup))
  return match ? match[locale === 'vi' ? 2 : 1] : subgroup
}

export function singleDrugGroupDisplay(
  name: string,
  classLabel: string | undefined,
  locale: ClinicalDecisionSupportLocale,
): string {
  const classCode = classLabel?.trim().match(/^(?:drug class|class|nhóm thuốc)?\s*([ABCD])$/i)?.[1]
  if (classCode) return drugClassDisplay(classCode, classLabel ?? name, locale)
  const catalogGroup = drugSubgroupDisplay(classLabel, locale)
  if (catalogGroup && catalogGroup.toLocaleLowerCase() !== name.toLocaleLowerCase()) return catalogGroup
  return locale === 'vi' ? 'Thuốc hạ áp' : 'Antihypertensive medicine'
}
