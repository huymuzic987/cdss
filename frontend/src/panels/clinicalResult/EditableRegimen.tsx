import { useMemo, useState } from 'react'
import type { CatalogGroup } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, FinalRegimenOption } from '../clinicalPresentation/types'
import { RegimenCatalogDrawer } from './RegimenCatalogDrawer'
import { RegimenOptionRow } from './RegimenOptionRow'
import { parseDragData, type DragSelection } from './regimenEditorTypes'
import { componentKey, displayComponent, selectionComponent, strategyLabel } from './regimenEditorUtils'

interface EditableRegimenProps {
  locale: ClinicalDecisionSupportLocale
  options: FinalRegimenOption[]
  catalog: CatalogGroup[]
  catalogOpen: boolean
  catalogLoading: boolean
  catalogError?: string
  onCatalogOpenChange: (open: boolean) => void
  onChange: (options: FinalRegimenOption[]) => void
}

export function EditableRegimen({
  locale, options, catalog, catalogOpen, catalogLoading, catalogError, onCatalogOpenChange, onChange,
}: EditableRegimenProps) {
  const [dragging, setDragging] = useState(false)
  const [dragOverOption, setDragOverOption] = useState<string | null>(null)
  const [selected, setSelected] = useState<{ optionId: string, component: FinalRegimenComponent } | null>(null)
  const vi = locale === 'vi'
  const selectedDetails = useMemo(() => {
    if (!selected) return []
    const group = catalog.find((item) => item.code === selected.component.group)
    if (!group) return []
    if (selected.component.medicineId) return group.subgroups.flatMap((item) => item.medicines).filter((item) => item.drug_id === selected.component.medicineId)
    if (selected.component.selectorKind === 'subgroup' && selected.component.subgroup) return group.subgroups.find((item) => item.name === selected.component.subgroup)?.medicines ?? []
    return group.subgroups.flatMap((item) => item.medicines)
  }, [catalog, selected])

  const addOption = () => onChange([...options, { id: `regimen-option-${Date.now()}`, components: [] }])
  const removeOption = (optionId: string) => {
    onChange(options.filter((option) => option.id !== optionId))
    if (selected?.optionId === optionId) setSelected(null)
  }
  const updateDose = (optionId: string, componentIndex: number, strategy: FinalRegimenComponent['doseStrategy']) => onChange(options.map((option) => option.id !== optionId ? option : {
    ...option,
    components: option.components.map((component, index) => index !== componentIndex ? component : {
      ...component,
      doseStrategy: strategy,
      dose: component.medicineId
        ? (catalog.find((group) => group.code === component.group)?.subgroups.flatMap((item) => item.medicines).find((item) => item.drug_id === component.medicineId)?.[strategy === 'MAX_DOSE' ? 'dose_max' : strategy === 'USUAL_DOSE' ? 'dose_usual' : 'dose_low'] ?? strategyLabel(strategy, locale))
        : strategyLabel(strategy, locale),
    }),
  }))
  const addSelection = (optionId: string, selection: DragSelection) => {
    const component = selectionComponent(selection, catalog)
    if (!component) return
    onChange(options.map((option) => option.id !== optionId || option.components.some((item) => componentKey(item) === componentKey(component)) ? option : { ...option, components: [...option.components, component] }))
  }
  const removeComponent = (optionId: string, componentIndex: number) => {
    onChange(options.map((option) => option.id !== optionId ? option : { ...option, components: option.components.filter((_, index) => index !== componentIndex) }))
    setSelected(null)
  }
  const startDrag = (event: React.DragEvent, payload: string) => {
    event.dataTransfer.setData('application/json', payload)
    event.dataTransfer.effectAllowed = 'copyMove'
    setDragging(true)
  }
  const finishDrag = () => { setDragging(false); setDragOverOption(null) }
  const dropOnOption = (event: React.DragEvent, optionId: string) => {
    event.preventDefault()
    const payload = parseDragData(event.dataTransfer.getData('application/json'))
    if (payload?.source === 'catalog') addSelection(optionId, payload)
    setDragOverOption(null)
  }
  const dropOnRemove = (event: React.DragEvent) => {
    event.preventDefault()
    const payload = parseDragData(event.dataTransfer.getData('application/json'))
    if (payload?.source === 'row' && payload.optionId !== undefined && payload.componentIndex !== undefined) removeComponent(payload.optionId, payload.componentIndex)
    finishDrag()
  }
  return (
    <div className="cds-editable-regimen">
      <div className="cds-regimen-editor-guidance">{vi ? 'Kéo nhóm, phân nhóm hoặc thuốc vào từng lựa chọn phác đồ.' : 'Drag a group, subgroup, or medicine into each regimen option.'}</div>
      {options.map((option, optionIndex) => <RegimenOptionRow key={option.id} option={option} optionIndex={optionIndex} optionCount={options.length} catalog={catalog} locale={locale} dragOver={dragOverOption === option.id} onDragOver={() => setDragOverOption(option.id)} onDrop={(event) => dropOnOption(event, option.id)} onRemove={() => removeOption(option.id)} onDragStart={(event, componentIndex) => startDrag(event, JSON.stringify({ source: 'row', optionId: option.id, componentIndex }))} onDragEnd={finishDrag} onSelect={(component) => setSelected({ optionId: option.id, component })} onDoseChange={(componentIndex, strategy) => updateDose(option.id, componentIndex, strategy)} />)}
      <button type="button" className="cds-editor-secondary-button" onClick={addOption}>+ {vi ? 'Thêm lựa chọn' : 'Add option'}</button>
      {dragging && <div className="cds-regimen-remove-zone" onDragOver={(event) => event.preventDefault()} onDrop={dropOnRemove}>{vi ? 'Thả vào đây để xóa' : 'Drop here to remove'}</div>}
      {selected && <div className="cds-regimen-component-inspector"><strong>{vi ? 'Chi tiết thành phần' : 'Component details'}</strong><span>{displayComponent(selected.component, catalog, locale).label} · {displayComponent(selected.component, catalog, locale).detail}</span><div className="cds-regimen-inspector-list">{selectedDetails.length === 0 && <span>{vi ? 'Không có dữ liệu danh mục.' : 'No catalog details available.'}</span>}{selectedDetails.map((medicine) => <span key={medicine.drug_id}>{medicine.name} · {medicine.subgroup ?? ''}</span>)}</div></div>}
      {catalogOpen && <RegimenCatalogDrawer locale={locale} catalog={catalog} loading={catalogLoading} error={catalogError} onClose={() => onCatalogOpenChange(false)} onDragStart={startDrag} onDragEnd={finishDrag} />}
    </div>
  )
}
