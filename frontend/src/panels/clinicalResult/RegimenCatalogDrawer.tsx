import { useState } from 'react'
import type { CatalogGroup } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { catalogDragData } from './regimenEditorTypes'

interface RegimenCatalogDrawerProps {
  locale: ClinicalDecisionSupportLocale
  catalog: CatalogGroup[]
  loading: boolean
  error?: string
  onClose: () => void
  onDragStart: (event: React.DragEvent, payload: string) => void
  onDragEnd: () => void
}

export function RegimenCatalogDrawer({ locale, catalog, loading, error, onClose, onDragStart, onDragEnd }: RegimenCatalogDrawerProps) {
  const [activeGroup, setActiveGroup] = useState<string | null>(null)
  const [activeSubgroup, setActiveSubgroup] = useState<string | null>(null)
  const vi = locale === 'vi'
  const group = catalog.find((item) => item.code === activeGroup)
  const subgroup = group?.subgroups.find((item) => item.name === activeSubgroup)
  return (
    <div className="cds-catalog-drawer" role="dialog" aria-label={vi ? 'Danh mục thuốc' : 'Medicine catalog'}>
      <div className="cds-editor-drawer-heading"><strong>{vi ? 'Danh mục thuốc' : 'Medicine catalog'}</strong><button type="button" onClick={onClose}>×</button></div>
      {loading && <p className="cds-empty">{vi ? 'Đang tải…' : 'Loading…'}</p>}
      {error && <p className="cds-editor-validation-error">{error}</p>}
      {!loading && !error && <div className="cds-catalog-columns">
        <CatalogColumn title={vi ? 'Nhóm thuốc' : 'Drug groups'}>
          {catalog.map((item) => <button type="button" className={activeGroup === item.code ? 'active' : ''} key={item.code} draggable onDragStart={(event) => onDragStart(event, catalogDragData({ selectorKind: 'group', groupCode: item.code }))} onDragEnd={onDragEnd} onClick={() => { setActiveGroup(item.code); setActiveSubgroup(null) }}>{vi ? item.label_vi : item.label_en}</button>)}
        </CatalogColumn>
        {group && <CatalogColumn title={vi ? 'Phân nhóm' : 'Subgroups'}>
          {group.subgroups.map((item) => <button type="button" className={activeSubgroup === item.name ? 'active' : ''} key={item.name} draggable onDragStart={(event) => onDragStart(event, catalogDragData({ selectorKind: 'subgroup', groupCode: group.code, subgroup: item.name }))} onDragEnd={onDragEnd} onClick={() => setActiveSubgroup(item.name)}>{item.name}</button>)}
        </CatalogColumn>}
        {group && subgroup && <CatalogColumn title={vi ? 'Thuốc' : 'Medicines'}>
          {subgroup.medicines.map((medicine) => <button type="button" key={medicine.drug_id} draggable onDragStart={(event) => onDragStart(event, catalogDragData({ selectorKind: 'medicine', groupCode: group.code, subgroup: subgroup.name, medicineId: medicine.drug_id }))} onDragEnd={onDragEnd}><span>{medicine.name}</span><small>{medicine.dose_low ?? ''}</small></button>)}
        </CatalogColumn>}
      </div>}
    </div>
  )
}

function CatalogColumn({ title, children }: { title: string, children: React.ReactNode }) {
  return <div className="cds-catalog-column"><strong>{title}</strong>{children}</div>
}
