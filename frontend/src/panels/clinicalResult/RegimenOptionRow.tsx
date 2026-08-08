import type { CatalogGroup } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, FinalRegimenOption } from '../clinicalPresentation/types'
import { RegimenComponentSummary } from './RegimenComponentSummary'
import { componentKey, displayComponent, editorComponentSummary, strategyLabel } from './regimenEditorUtils'

interface RegimenOptionRowProps {
  option: FinalRegimenOption
  optionIndex: number
  optionCount: number
  catalog: CatalogGroup[]
  currentSubgroups: Record<string, string[]>
  baselineSubgroups: Record<string, string[]>
  locale: ClinicalDecisionSupportLocale
  dragOver: boolean
  onDragOver: () => void
  onDragLeave: () => void
  onDrop: (event: React.DragEvent) => void
  onRemove: () => void
  onDragStart: (event: React.DragEvent, componentIndex: number) => void
  onDragEnd: () => void
  onSelect: (component: FinalRegimenComponent, anchor: HTMLElement) => void
  onDoseChange: (componentIndex: number, strategy: FinalRegimenComponent['doseStrategy']) => void
}

export function RegimenOptionRow({
  option, optionIndex, optionCount, catalog, currentSubgroups, baselineSubgroups, locale, dragOver, onDragOver, onDragLeave, onDrop, onRemove,
  onDragStart, onDragEnd, onSelect, onDoseChange,
}: RegimenOptionRowProps) {
  const vi = locale === 'vi'
  return (
    <div className={`cds-regimen-drop-row ${dragOver ? 'is-drag-over' : ''}`} onDragOver={(event) => { event.preventDefault(); onDragOver() }} onDragLeave={onDragLeave} onDrop={onDrop}>
      <div className="cds-regimen-drop-row-heading"><strong>{vi ? `Lựa chọn ${optionIndex + 1}` : `Option ${optionIndex + 1}`}</strong><button type="button" onClick={onRemove} disabled={optionCount <= 1}>{vi ? 'Xóa lựa chọn' : 'Remove option'}</button></div>
      <div className="cds-editable-regimen-components">
        {option.components.length === 0 && <span className="cds-regimen-drop-hint">{vi ? 'Thả thành phần vào đây' : 'Drop components here'}</span>}
        {option.components.map((rawComponent, componentIndex) => {
          const component = displayComponent(rawComponent, catalog, locale)
          const summary = editorComponentSummary(rawComponent, catalog, locale, rawComponent.isCustom ? currentSubgroups : baselineSubgroups)
          return (
            <div className="cds-editable-regimen-chip" key={`${componentKey(component)}-${componentIndex}`}>
              <button type="button" draggable onDragStart={(event) => onDragStart(event, componentIndex)} onDragEnd={onDragEnd} onClick={(event) => onSelect(rawComponent, event.currentTarget)} title={vi ? 'Xem chi tiết và kéo để xóa' : 'Click for details; drag to remove'}><RegimenComponentSummary editor locale={locale} {...summary} /></button>
              <select aria-label={`${component.label} dose`} value={component.doseStrategy ?? 'LOW_DOSE'} onChange={(event) => onDoseChange(componentIndex, event.target.value as FinalRegimenComponent['doseStrategy'])}>
                <option value="LOW_DOSE">{strategyLabel('LOW_DOSE', locale)}</option><option value="USUAL_DOSE">{strategyLabel('USUAL_DOSE', locale)}</option><option value="MAX_DOSE">{strategyLabel('MAX_DOSE', locale)}</option>
              </select>
            </div>
          )
        })}
      </div>
    </div>
  )
}
