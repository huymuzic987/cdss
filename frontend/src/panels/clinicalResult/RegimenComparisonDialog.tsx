import type { RejectionReasonCode } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'

interface ReasonLabel { code: RejectionReasonCode, en: string, vi: string }

interface RegimenComparisonDialogProps {
  locale: ClinicalDecisionSupportLocale
  baselineRows: string[]
  customRows: string[]
  reasons: RejectionReasonCode[]
  reasonCodes: ReasonLabel[]
  saving: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function RegimenComparisonDialog({ locale, baselineRows, customRows, reasons, reasonCodes, saving, onCancel, onConfirm }: RegimenComparisonDialogProps) {
  const vi = locale === 'vi'
  const labels = reasons.map((code) => reasonCodes.find((reason) => reason.code === code)?.[vi ? 'vi' : 'en']).filter(Boolean).join(', ')
  return <div className="cds-comparison-overlay" role="dialog" aria-modal="true" aria-label={vi ? 'So sánh phác đồ' : 'Compare regimens'}>
    <div className="cds-comparison-dialog">
      <h2>{vi ? 'So sánh trước khi lưu' : 'Compare before saving'}</h2>
      <div className="cds-comparison-columns"><ComparisonColumn title={vi ? 'Phác đồ mặc định' : 'Default regimen'} rows={baselineRows} locale={locale} /><ComparisonColumn title={vi ? 'Phác đồ tùy chỉnh' : 'Custom regimen'} rows={customRows} locale={locale} /></div>
      <div className="cds-comparison-reasons"><strong>{vi ? 'Lý do:' : 'Reasons:'}</strong> {labels}</div>
      <div className="cds-editor-actions"><button type="button" onClick={onCancel} disabled={saving}>{vi ? 'Hủy' : 'Cancel'}</button><button type="button" className="primary" onClick={onConfirm} disabled={saving}>{saving ? (vi ? 'Đang lưu…' : 'Saving…') : (vi ? 'Xác nhận và lưu' : 'Confirm and save')}</button></div>
    </div>
  </div>
}

function ComparisonColumn({ title, rows, locale }: { title: string, rows: string[], locale: ClinicalDecisionSupportLocale }) {
  return <div><h3>{title}</h3>{rows.length === 0 ? <p>{locale === 'vi' ? 'Trống' : 'Empty'}</p> : rows.map((row, index) => <p key={`${row}-${index}`}>{row}</p>)}</div>
}
