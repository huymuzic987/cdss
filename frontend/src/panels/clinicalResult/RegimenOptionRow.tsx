import type { CatalogGroup } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, FinalRegimenOption } from '../clinicalPresentation/types'
import { componentKey, displayComponent, strategyLabel } from './regimenEditorUtils'

interface RegimenOptionRowProps {
  option: FinalRegimenOption
  optionIndex: number
  optionCount: number
  catalog: CatalogGroup[]
  locale: ClinicalDecisionSupportLocale
  dragOver: boolean
  onDragOver: () => void
  onDrop: (event: React.DragEvent) => void
  onRemove: () => void
  onDragStart: (event: React.DragEvent, componentIndex: number) => void
  onDragEnd: () => void
  onSelect: (component: FinalRegimenComponent) => void
  onDoseChange: (componentIndex: number, strategy: FinalRegimenComponent['doseStrategy']) => void
}

export function RegimenOptionRow({
  option, optionIndex, optionCount, catalog, locale, dragOver, onDragOver, onDrop, onRemove,
  onDragStart, onDragEnd, onSelect, onDoseChange,
}: RegimenOptionRowProps) {
  const vi = locale === 'vi'
  return (
    <div className={`cds-regimen-drop-row ${dragOver ? 'is-drag-over' : ''}`} onDragOver={(event) => { event.preventDefault(); onDragOver() }} onDragLeave={onDragOver} onDrop={onDrop}>
      <div className="cds-regimen-drop-row-heading"><strong>{vi ? `Lựa chọn ${optionIndex + 1}` : `Option ${optionIndex + 1}`}</strong><button type="button" onClick={onRemove} disabled={optionCount <= 1}>{vi ? 'Xóa lựa chọn' : 'Remove option'}</button></div>
      <div className="cds-editable-regimen-components">
        {option.components.length === 0 && <span className="cds-regimen-drop-hint">{vi ? 'Thả thành phần vào đây' : 'Drop components here'}</span>}
        {option.components.map((rawComponent, componentIndex) => {
          const component = displayComponent(rawComponent, catalog, locale)
          return (
            <div className="cds-editable-regimen-chip" key={`${componentKey(component)}-${componentIndex}`}>
              <button type="button" draggable onDragStart={(event) => onDragStart(event, componentIndex)} onDragEnd={onDragEnd} onClick={() => onSelect(rawComponent)} title={vi ? 'Xem chi tiết và kéo để xóa' : 'Click for details; drag to remove'}><strong>{component.label}</strong><small>{component.detail}</small></button>
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
