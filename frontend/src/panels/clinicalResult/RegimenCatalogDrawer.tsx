import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { CatalogGroup } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { catalogDragData } from './regimenEditorTypes'

interface RegimenCatalogDrawerProps {
  locale: ClinicalDecisionSupportLocale
  catalog: CatalogGroup[]
  loading: boolean
  error?: string
  dragging: boolean
  onClose: () => void
  onDragStart: (event: React.DragEvent, payload: string) => void
  onDragEnd: () => void
}

export function RegimenCatalogDrawer({ locale, catalog, loading, error, dragging, onClose, onDragStart, onDragEnd }: RegimenCatalogDrawerProps) {
  const [activeGroup, setActiveGroup] = useState<string | null>(null)
  const [activeSubgroup, setActiveSubgroup] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const drawerRef = useRef<HTMLDivElement>(null)
  const vi = locale === 'vi'
  const group = catalog.find((item) => item.code === activeGroup)
  const subgroup = group?.subgroups.find((item) => item.name === activeSubgroup)
  const searchResults = useMemo(() => {
    const query = normalizeSearch(search)
    if (!query) return []
    return catalog.flatMap((item) => item.subgroups.flatMap((subgroupItem) => subgroupItem.medicines
      .filter((medicine) => normalizeSearch(medicine.name).includes(query))
      .map((medicine) => ({ groupCode: item.code, subgroup: subgroupItem.name, medicine }))))
  }, [catalog, search])

  useEffect(() => {
    const dismissOutside = (event: MouseEvent) => {
      if (!(event.target instanceof Node) || drawerRef.current?.contains(event.target)) return
      onClose()
    }
    document.addEventListener('click', dismissOutside)
    return () => document.removeEventListener('click', dismissOutside)
  }, [onClose])

  const startCatalogDrag = (event: React.DragEvent, payload: string) => {
    onDragStart(event, payload)
  }

  return createPortal(
    <div className={`cds-catalog-drawer-host${dragging ? ' is-dragging' : ''}`}>
    <div ref={drawerRef} className="cds-catalog-drawer" role="dialog" aria-label={vi ? 'Danh mục thuốc' : 'Medicine catalog'} onKeyDown={(event) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose()
      }
    }}>
      <div className="cds-editor-drawer-heading"><strong>{vi ? 'Danh mục thuốc' : 'Medicine catalog'}</strong><button type="button" onClick={onClose}>×</button></div>
      {loading && <p className="cds-empty">{vi ? 'Đang tải…' : 'Loading…'}</p>}
      {error && <p className="cds-editor-validation-error">{error}</p>}
      {!loading && !error && <>
        <label className="cds-catalog-search"><span>{vi ? 'Tìm thuốc theo tên' : 'Search medicines by name'}</span><input type="search" aria-label={vi ? 'Tìm thuốc' : 'Search medicines'} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={vi ? 'Nhập tên thuốc…' : 'Type a medicine name…'} /></label>
        <div className={`cds-catalog-content${search.trim() ? ' is-searching' : ''}`}><div className="cds-catalog-columns">
        <CatalogColumn title={vi ? 'Nhóm thuốc' : 'Drug groups'}>
          {catalog.map((item) => <button type="button" className={activeGroup === item.code ? 'active' : ''} key={item.code} draggable onDragStart={(event) => startCatalogDrag(event, catalogDragData({ selectorKind: 'group', groupCode: item.code }))} onDragEnd={onDragEnd} onClick={() => { setActiveGroup((current) => current === item.code ? null : item.code); setActiveSubgroup(null) }}><span>{vi ? item.label_vi : item.label_en}</span><small>{item.subgroups.length} {vi ? 'phân nhóm · liều thấp' : 'subgroups · low dose'}</small></button>)}
        </CatalogColumn>
        {group && <CatalogColumn title={vi ? 'Phân nhóm' : 'Subgroups'}>
          {group.subgroups.map((item) => <button type="button" className={activeSubgroup === item.name ? 'active' : ''} key={item.name} draggable onDragStart={(event) => startCatalogDrag(event, catalogDragData({ selectorKind: 'subgroup', groupCode: group.code, subgroup: item.name }))} onDragEnd={onDragEnd} onClick={() => setActiveSubgroup((current) => current === item.name ? null : item.name)}><span>{item.name}</span><small>{item.medicines.length} {vi ? 'thuốc · liều thấp' : 'drugs · low dose'}</small></button>)}
        </CatalogColumn>}
        {group && subgroup && <CatalogColumn title={vi ? 'Thuốc' : 'Medicines'}>
          {subgroup.medicines.map((medicine) => <button type="button" key={medicine.drug_id} draggable onDragStart={(event) => startCatalogDrag(event, catalogDragData({ selectorKind: 'medicine', groupCode: group.code, subgroup: subgroup.name, medicineId: medicine.drug_id }))} onDragEnd={onDragEnd}><span>{medicine.name}</span><small>{medicine.dose_low ?? '-'} / {medicine.dose_usual ?? '-'} / {medicine.dose_max ?? '-'}</small></button>)}
        </CatalogColumn>}
        </div>{search.trim() && <CatalogColumn title={vi ? `Kết quả (${searchResults.length})` : `Matching medicines (${searchResults.length})`}>
          {searchResults.length === 0 && <p className="cds-catalog-empty-search">{vi ? 'Không tìm thấy thuốc.' : 'No medicines found.'}</p>}
          {searchResults.map(({ groupCode, subgroup: subgroupName, medicine }) => <button type="button" key={`${groupCode}:${subgroupName}:${medicine.drug_id}`} draggable onDragStart={(event) => startCatalogDrag(event, catalogDragData({ selectorKind: 'medicine', groupCode, subgroup: subgroupName, medicineId: medicine.drug_id }))} onDragEnd={onDragEnd}><span>{medicine.name}</span><small>{groupCode} · {subgroupName} · {medicine.dose_low ?? '-'} / {medicine.dose_usual ?? '-'} / {medicine.dose_max ?? '-'}</small></button>)}
        </CatalogColumn>}</div></>}
    </div></div>,
    document.body,
  )
}

function CatalogColumn({ title, children }: { title: string, children: React.ReactNode }) {
  return <div className="cds-catalog-column"><strong>{title}</strong>{children}</div>
}

function normalizeSearch(value: string): string {
  return value.toLocaleLowerCase().normalize('NFKD').replace(/\p{M}/gu, '').trim()
}
