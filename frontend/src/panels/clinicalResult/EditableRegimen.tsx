import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { CatalogGroup } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import type { FinalRegimenComponent, FinalRegimenOption } from '../clinicalPresentation/types'
import { RegimenCatalogDrawer } from './RegimenCatalogDrawer'
import { ComponentCatalogDetails } from './RegimenCatalogPopup'
import { RegimenOptionRow } from './RegimenOptionRow'
import { RegimenSafetyWarningPanel } from './RegimenSafetyWarningPanel'
import { parseDragData, type DragSelection } from './regimenEditorTypes'
import { componentKey, displayComponent, editorPresentationCatalog, selectionComponent, strategyLabel } from './regimenEditorUtils'
import type { RegimenSafetyWarning } from './regimenSafetyWarnings'

const warningOrder: Record<RegimenSafetyWarning['severity'], number> = { ABSOLUTE: 3, RELATIVE: 2, INSUFFICIENT_DATA: 1 }

interface EditableRegimenProps {
  locale: ClinicalDecisionSupportLocale
  options: FinalRegimenOption[]
  catalog: CatalogGroup[]
  currentSubgroups: Record<string, string[]>
  baselineSubgroups: Record<string, string[]>
  catalogOpen: boolean
  catalogLoading: boolean
  catalogError?: string
  safetyWarnings: (component: FinalRegimenComponent) => RegimenSafetyWarning[]
  onCatalogOpenChange: (open: boolean) => void
  onChange: (options: FinalRegimenOption[]) => void
}

interface SelectedComponent {
  optionId: string
  component: FinalRegimenComponent
  anchor: HTMLElement
  position: { left: number, top: number }
  placement: 'above' | 'below'
}

export function EditableRegimen({
  locale, options, catalog, currentSubgroups, baselineSubgroups, catalogOpen, catalogLoading, catalogError, safetyWarnings, onCatalogOpenChange, onChange,
}: EditableRegimenProps) {
  const [dragging, setDragging] = useState(false)
  const [dragOverOption, setDragOverOption] = useState<string | null>(null)
  const [selected, setSelected] = useState<SelectedComponent | null>(null)
  const selectedPopupRef = useRef<HTMLDivElement | null>(null)
  const dragPayloadRef = useRef<string | null>(null)
  const dropHandledRef = useRef(false)
  const dragStartTimerRef = useRef<number | null>(null)
  const vi = locale === 'vi'
  const detailCatalog = useMemo(() => editorPresentationCatalog(catalog), [catalog])
  const regimenWarnings = useMemo(() => Array.from(new Map(
    options.flatMap((option) => option.components.flatMap((component) => safetyWarnings(component)))
      .map((warning) => [`${warning.severity}:${warning.text}`, warning] as const),
  ).values()).sort((left, right) => warningOrder[right.severity] - warningOrder[left.severity]), [options, safetyWarnings])

  useEffect(() => {
    if (!selected) return
    const dismissOutside = (event: PointerEvent) => {
      if (!(event.target instanceof Node)) return
      if (selected.anchor.contains(event.target) || selectedPopupRef.current?.contains(event.target)) return
      setSelected(null)
    }
    document.addEventListener('pointerdown', dismissOutside)
    return () => document.removeEventListener('pointerdown', dismissOutside)
  }, [selected])

  const addOption = () => onChange([...options, { id: `regimen-option-${Date.now()}`, components: [] }])
  const removeOption = (optionId: string) => {
    onChange(options.filter((option) => option.id !== optionId))
    if (selected?.optionId === optionId) setSelected(null)
  }
  const selectComponent = (optionId: string, component: FinalRegimenComponent, anchor: HTMLElement) => {
    if (selected?.anchor === anchor) {
      setSelected(null)
      return
    }
    const rect = anchor.getBoundingClientRect()
    const popupWidth = Math.min(620, window.innerWidth - 32)
    const estimatedHeight = 360
    const placement = rect.bottom + estimatedHeight > window.innerHeight && rect.top > estimatedHeight ? 'above' : 'below'
    setSelected({
      optionId,
      component,
      anchor,
      position: {
        left: Math.max(16, Math.min(rect.left, window.innerWidth - popupWidth - 16)),
        top: placement === 'above' ? rect.top - 8 : rect.bottom + 8,
      },
      placement,
    })
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
    onChange(options.map((option) => {
      if (option.id !== optionId) return option
      if (option.components.some((item) => componentKey(item) === componentKey(component))) return option
      if (selection.selectorKind !== 'subgroup' || !selection.subgroup) return { ...option, components: [...option.components, component] }
      const targetIndex = option.components.findIndex((item) => item.group === component.group && !item.medicineId)
      if (targetIndex < 0) return { ...option, components: [...option.components, component] }
      const target = option.components[targetIndex]
      const existingSubgroups = target.isCustom
        ? target.subgroup?.split('/').map((item) => item.trim()).filter(Boolean) ?? []
        : baselineSubgroups[target.group] ?? target.subgroup?.split('/').map((item) => item.trim()).filter(Boolean) ?? []
      const subgroups = Array.from(new Set([...existingSubgroups, selection.subgroup]))
      return {
        ...option,
        components: option.components.map((item, index) => index !== targetIndex ? item : {
          ...item,
          label: component.label,
          detail: subgroups.join(' / '),
          subgroup: subgroups.join(' / '),
          selectorKind: 'subgroup' as const,
          isCustom: true,
        }),
      }
    }))
  }
  const removeComponent = useCallback((optionId: string, componentIndex: number) => {
    onChange(options.map((option) => option.id !== optionId ? option : { ...option, components: option.components.filter((_, index) => index !== componentIndex) }))
    setSelected(null)
  }, [onChange, options])
  const startDrag = (event: React.DragEvent, payload: string) => {
    event.dataTransfer.setData('application/json', payload)
    event.dataTransfer.effectAllowed = 'copyMove'
    dragPayloadRef.current = payload
    dropHandledRef.current = false
    if (dragStartTimerRef.current !== null) window.clearTimeout(dragStartTimerRef.current)
    dragStartTimerRef.current = window.setTimeout(() => {
      dragStartTimerRef.current = null
      setDragging(true)
    }, 0)
  }
  const finishDrag = () => {
    if (dragStartTimerRef.current !== null) {
      window.clearTimeout(dragStartTimerRef.current)
      dragStartTimerRef.current = null
    }
    setDragging(false)
    setDragOverOption(null)
    dragPayloadRef.current = null
  }
  useEffect(() => {
    if (!dragging) return
    const finishFromDocument = (event: DragEvent) => {
      if (!dropHandledRef.current && (event.type === 'drop' || event.type === 'dragend')) {
        const payload = parseDragData(dragPayloadRef.current ?? event.dataTransfer?.getData('application/json') ?? '')
        if (payload?.source === 'row' && payload.optionId !== undefined && payload.componentIndex !== undefined) {
          removeComponent(payload.optionId, payload.componentIndex)
        }
      }
      dropHandledRef.current = true
      finishDrag()
    }
    document.addEventListener('dragend', finishFromDocument, true)
    document.addEventListener('drop', finishFromDocument)
    return () => {
      document.removeEventListener('dragend', finishFromDocument, true)
      document.removeEventListener('drop', finishFromDocument)
    }
  }, [dragging, removeComponent])
  const dropOnOption = (event: React.DragEvent, optionId: string) => {
    event.preventDefault()
    dropHandledRef.current = true
    const payload = parseDragData(event.dataTransfer.getData('application/json'))
    if (payload?.source === 'catalog') addSelection(optionId, payload)
    finishDrag()
  }
  const dropOnRemove = (event: React.DragEvent) => {
    event.preventDefault()
    dropHandledRef.current = true
    const payload = parseDragData(event.dataTransfer.getData('application/json'))
    if (payload?.source === 'row' && payload.optionId !== undefined && payload.componentIndex !== undefined) removeComponent(payload.optionId, payload.componentIndex)
    finishDrag()
  }
  return (
    <div className="cds-editable-regimen">
      <div className="cds-regimen-editor-guidance">{vi ? 'Kéo nhóm, phân nhóm hoặc thuốc vào từng lựa chọn phác đồ.' : 'Drag a group, subgroup, or medicine into each regimen option.'}</div>
      {options.map((option, optionIndex) => <RegimenOptionRow key={option.id} option={option} optionIndex={optionIndex} optionCount={options.length} catalog={catalog} currentSubgroups={currentSubgroups} baselineSubgroups={baselineSubgroups} locale={locale} dragOver={dragOverOption === option.id} onDragOver={() => setDragOverOption(option.id)} onDragLeave={() => setDragOverOption(null)} onDrop={(event) => dropOnOption(event, option.id)} onRemove={() => removeOption(option.id)} onDragStart={(event, componentIndex) => startDrag(event, JSON.stringify({ source: 'row', optionId: option.id, componentIndex }))} onDragEnd={finishDrag} onSelect={(component, anchor) => selectComponent(option.id, component, anchor)} onDoseChange={(componentIndex, strategy) => updateDose(option.id, componentIndex, strategy)} />)}
      <button type="button" className="cds-editor-secondary-button" onClick={addOption}>+ {vi ? 'Thêm lựa chọn' : 'Add option'}</button>
      <RegimenSafetyWarningPanel locale={locale} warnings={regimenWarnings} />
      {dragging && <div className="cds-regimen-remove-zone" onDragOver={(event) => event.preventDefault()} onDrop={dropOnRemove}>{vi ? 'Thả vào đây để xóa' : 'Drop here to remove'}</div>}
      {catalogOpen && <RegimenCatalogDrawer locale={locale} catalog={catalog} loading={catalogLoading} error={catalogError} dragging={dragging} onClose={() => onCatalogOpenChange(false)} onDragStart={startDrag} onDragEnd={finishDrag} />}
      {selected && createPortal(<div ref={selectedPopupRef} className="cds-editor-component-popup-shell"><ComponentCatalogDetails component={displayComponent(selected.component, catalog, locale)} catalog={detailCatalog} placement={selected.placement} position={selected.position} onClose={() => setSelected(null)} /></div>, document.body)}
    </div>
  )
}
