import type { ClinicalCode } from '../clinicalCodes'

interface ClinicalCodeListProps {
  codes: ClinicalCode[]
  compact?: boolean
}

export function ClinicalCodeList({ codes, compact = false }: ClinicalCodeListProps) {
  if (codes.length === 0) return null

  return (
    <div className={compact ? 'clinical-code-list compact' : 'clinical-code-list'}>
      {codes.map((code) => (
        <div className="clinical-code-entry" key={code.symptomId}>
          <div className="clinical-code-name">{code.nameEn || code.nameVi}</div>
          <div className="clinical-code-values">
            {code.icd10 && <span><strong>ICD-10</strong> {code.icd10}</span>}
            {code.snomedCt && <span><strong>SNOMED CT</strong> {code.snomedCt}</span>}
            {code.loinc && <span><strong>LOINC</strong> {code.loinc}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
