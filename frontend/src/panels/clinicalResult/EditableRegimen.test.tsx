// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CatalogGroup } from '../../api/types'
import { EditableRegimen } from './EditableRegimen'

const catalog: CatalogGroup[] = [{
  code: 'D', label_en: 'Diuretic', label_vi: 'Lợi tiểu', subgroups: [{
    name: 'Thiazide', medicines: [{
      drug_id: 'hydrochlorothiazide', name: 'Hydrochlorothiazide', group_code: 'D', subgroup: 'Thiazide',
      route: 'Oral', dose_low: '12.5 mg', dose_usual: '25 mg', dose_max: '50 mg', available: true, snomed_code: null,
    }],
  }],
}]

const similarSubgroupCatalog: CatalogGroup[] = [{
  code: 'D', label_en: 'Diuretics', label_vi: 'Lợi tiểu', subgroups: [
    { name: 'LT Thiazide', medicines: [] },
    { name: 'LT Thiazide-like', medicines: [] },
    { name: 'LT quai', medicines: [] },
    { name: 'LT giữ Kali', medicines: [] },
  ],
}]

afterEach(() => cleanup())

describe('EditableRegimen drag behavior', () => {
  it('allows catalog dragging and restores the catalog after dropping into an option', async () => {
    let payload = ''
    const dataTransfer = {
      effectAllowed: '',
      setData: (_type: string, value: string) => { payload = value },
      getData: () => payload,
    }
    const onChange = vi.fn()
    render(<EditableRegimen locale="en" options={[{ id: 'option-1', components: [] }]} catalog={catalog} currentSubgroups={{ D: ['Thiazide'] }} baselineSubgroups={{ D: ['Thiazide'] }} catalogOpen catalogLoading={false} safetyWarnings={() => []} onCatalogOpenChange={vi.fn()} onChange={onChange} />)

    const group = screen.getByRole('button', { name: /Diuretic/ })
    fireEvent.dragStart(group, { dataTransfer })
    await waitFor(() => expect(document.querySelector('.cds-catalog-drawer-host')).toHaveClass('is-dragging'))

    fireEvent.drop(document.querySelector('.cds-regimen-drop-row')!, { dataTransfer })
    expect(onChange).toHaveBeenCalledWith([{ id: 'option-1', components: [{ label: 'Diuretic', detail: 'Diuretic', group: 'D', dose: 'Low dose', selectorKind: 'group', doseStrategy: 'LOW_DOSE', isCustom: true }] }])
    await waitFor(() => expect(document.querySelector('.cds-catalog-drawer-host')).not.toHaveClass('is-dragging'))
  })

  it('filters the catalog by medicine name in real time', () => {
    render(<EditableRegimen locale="en" options={[{ id: 'option-1', components: [] }]} catalog={catalog} currentSubgroups={{ D: ['Thiazide'] }} baselineSubgroups={{ D: ['Thiazide'] }} catalogOpen catalogLoading={false} safetyWarnings={() => []} onCatalogOpenChange={vi.fn()} onChange={vi.fn()} />)

    const drawer = screen.getByRole('dialog', { name: 'Medicine catalog' })
    const search = within(drawer).getByRole('searchbox', { name: 'Search medicines' })
    fireEvent.change(search, { target: { value: 'hydro' } })
    expect(within(drawer).getByRole('button', { name: /Hydrochlorothiazide/ })).toBeTruthy()
    fireEvent.change(search, { target: { value: 'not-a-real-medicine' } })
    expect(within(drawer).getByText('No medicines found.')).toBeTruthy()
  })

  it('toggles group and subgroup tabs with repeated clicks', () => {
    render(<EditableRegimen locale="en" options={[{ id: 'option-1', components: [] }]} catalog={catalog} currentSubgroups={{ D: ['Thiazide'] }} baselineSubgroups={{ D: ['Thiazide'] }} catalogOpen catalogLoading={false} safetyWarnings={() => []} onCatalogOpenChange={vi.fn()} onChange={vi.fn()} />)

    const group = screen.getByRole('button', { name: /Diuretic/ })
    fireEvent.click(group)
    expect(screen.getByText('Subgroups')).toBeTruthy()
    fireEvent.click(group)
    expect(screen.queryByText('Subgroups')).toBeNull()

    fireEvent.click(group)
    const subgroup = screen.getByRole('button', { name: /Thiazide/ })
    fireEvent.click(subgroup)
    expect(screen.getByText('Medicines')).toBeTruthy()
    fireEvent.click(subgroup)
    expect(screen.queryByText('Medicines')).toBeNull()
  })

  it('removes an existing component when the drop happens outside an option', async () => {
    let payload = ''
    const dataTransfer = {
      effectAllowed: '',
      setData: (_type: string, value: string) => { payload = value },
      getData: () => payload,
    }
    const onChange = vi.fn()
    render(<EditableRegimen locale="en" options={[{ id: 'option-1', components: [{ label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose', selectorKind: 'group', doseStrategy: 'LOW_DOSE' }] }]} catalog={catalog} currentSubgroups={{ D: ['Thiazide'] }} baselineSubgroups={{ D: ['Thiazide'] }} catalogOpen={false} catalogLoading={false} safetyWarnings={() => []} onCatalogOpenChange={vi.fn()} onChange={onChange} />)

    const chip = document.querySelector('.cds-editable-regimen-chip > button')!
    fireEvent.dragStart(chip, { dataTransfer })
    await waitFor(() => expect(document.querySelector('.cds-regimen-remove-zone')).toBeTruthy())
    fireEvent.drop(document.body, { dataTransfer })

    expect(onChange).toHaveBeenCalledWith([{ id: 'option-1', components: [] }])
    await waitFor(() => expect(document.querySelector('.cds-regimen-remove-zone')).toBeNull())
  })

  it('opens component details as a dismissible popup', () => {
    render(<EditableRegimen locale="en" options={[{ id: 'option-1', components: [{ label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose', selectorKind: 'group', doseStrategy: 'LOW_DOSE' }] }]} catalog={catalog} currentSubgroups={{ D: ['Thiazide'] }} baselineSubgroups={{ D: ['Thiazide'] }} catalogOpen={false} catalogLoading={false} safetyWarnings={() => []} onCatalogOpenChange={vi.fn()} onChange={vi.fn()} />)

    fireEvent.click(document.querySelector('.cds-editable-regimen-chip > button')!)
    expect(screen.getByRole('dialog', { name: 'Diuretic drug details' })).toBeTruthy()
    fireEvent.pointerDown(document.body)
    expect(screen.queryByRole('dialog', { name: 'Diuretic drug details' })).toBeNull()
  })

  it('renders repeated safety warnings once at the section bottom', () => {
    render(<EditableRegimen locale="en" options={[
      { id: 'option-1', components: [{ label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose', selectorKind: 'group' }] },
      { id: 'option-2', components: [{ label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose', selectorKind: 'group' }] },
    ]} catalog={catalog} currentSubgroups={{ D: ['Thiazide'] }} baselineSubgroups={{ D: ['Thiazide'] }} catalogOpen={false} catalogLoading={false} safetyWarnings={() => [{ severity: 'ABSOLUTE', text: 'Absolute contraindication: Gout' }]} onCatalogOpenChange={vi.fn()} onChange={vi.fn()} />)

    expect(screen.getAllByRole('alert')).toHaveLength(1)
    expect(screen.getByRole('alert')).toHaveTextContent('Absolute contraindication: Gout')
  })

  it('adds only the dragged subgroup to an existing filtered group component', async () => {
    let payload = ''
    const dataTransfer = {
      effectAllowed: '',
      setData: (_type: string, value: string) => { payload = value },
      getData: () => payload,
    }
    const onChange = vi.fn()
    render(<EditableRegimen
      locale="en"
      options={[{ id: 'option-1', components: [{
        label: 'D', detail: 'Diuretic', group: 'D', dose: 'Low dose',
        subgroup: 'LT Thiazide / LT Thiazide-like / LT quai / LT giữ Kali', selectorKind: 'subgroup', doseStrategy: 'LOW_DOSE',
      }] }]}
      catalog={similarSubgroupCatalog}
      currentSubgroups={{ D: ['LT Thiazide', 'LT Thiazide-like', 'LT quai', 'LT giữ Kali'] }}
      baselineSubgroups={{ D: ['LT quai', 'LT giữ Kali'] }}
      catalogOpen
      catalogLoading={false}
      safetyWarnings={() => []}
      onCatalogOpenChange={vi.fn()}
      onChange={onChange}
    />)

    const drawer = screen.getByRole('dialog', { name: 'Medicine catalog' })
    fireEvent.click(within(drawer).getByRole('button', { name: /Diuretics/ }))
    const subgroup = within(drawer).getByRole('button', { name: /LT Thiazide-like/ })
    fireEvent.dragStart(subgroup, { dataTransfer })
    await waitFor(() => expect(document.querySelector('.cds-catalog-drawer-host')).toHaveClass('is-dragging'))
    fireEvent.drop(document.querySelector('.cds-regimen-drop-row')!, { dataTransfer })

    expect(onChange).toHaveBeenCalledWith([{ id: 'option-1', components: [{
      label: 'Diuretics', detail: 'LT quai / LT giữ Kali / LT Thiazide-like', group: 'D', dose: 'Low dose',
      subgroup: 'LT quai / LT giữ Kali / LT Thiazide-like', selectorKind: 'subgroup', doseStrategy: 'LOW_DOSE', isCustom: true,
    }] }])
  })
})
