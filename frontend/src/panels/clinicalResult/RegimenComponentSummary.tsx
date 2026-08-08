import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import './RegimenComponentSummary.css'

export type RegimenComponentKind = 'group' | 'subgroup' | 'medicine'

interface RegimenComponentSummaryProps {
  locale: ClinicalDecisionSupportLocale
  kind: RegimenComponentKind
  label: string
  clarification: string
  subgroups?: string
  dose: string
  inline?: boolean
  compact?: boolean
  compactLabel?: string
  editor?: boolean
  groupCode?: string
  subgroupLabel?: string
}

export function RegimenComponentSummary({ locale, kind, label, clarification, subgroups, dose, inline = false, compact = false, compactLabel, editor = false, groupCode, subgroupLabel }: RegimenComponentSummaryProps) {
  void locale
  if (inline) {
    if (compact) {
      return <>
        <strong className="cds-component-summary-inline-label">{compactLabel ?? label}</strong>
        <b className="cds-component-summary-dose">{dose}</b>
      </>
    }
    return <>
      <strong className="cds-component-summary-inline-label">{label}</strong>
      <small className="cds-component-summary-inline-clarification">{clarification}</small>
      {subgroups && <small className="cds-component-summary-inline-subgroups">{subgroups}</small>}
      <b className="cds-component-summary-dose">{dose}</b>
    </>
  }
  if (editor) {
    const context = kind === 'medicine'
      ? [groupCode, subgroupLabel].filter(Boolean).join(' · ')
      : subgroupLabel || clarification
    return (
      <span className="cds-component-summary cds-component-summary--editor">
        <strong className="cds-component-summary-label">{label}</strong>
        <small className="cds-component-summary-editor-context">{context}</small>
        <b className="cds-component-summary-dose">{dose}</b>
      </span>
    )
  }
  return (
    <span className="cds-component-summary">
      <span className="cds-component-summary-main">
        <strong><span className="cds-component-summary-label">{label}</span><small className="cds-component-summary-clarification">{clarification}</small></strong>
        {subgroups && <small className="cds-component-summary-subgroups">{subgroups}</small>}
      </span>
      <b className="cds-component-summary-dose">{dose}</b>
    </span>
  )
}
