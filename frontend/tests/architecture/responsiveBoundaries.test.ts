import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const FRONTEND_ROOT = join(process.cwd())

function read(relativePath: string): string {
  return readFileSync(join(FRONTEND_ROOT, relativePath), 'utf8')
}

describe('frontend responsive boundaries', () => {
  it('defines the mobile workbench drawer contract', () => {
    const collapse = read('src/styles/panel-collapse.css')
    const shell = read('src/styles/app-shell.css')
    const canvas = read('src/styles/canvas.css')
    const appCss = read('src/App.css')

    expect(collapse).toContain('@media (max-width: 780px)')
    expect(collapse).toContain('.mobile-drawer-open')
    expect(collapse).toContain('.mobile-drawer-backdrop')
    expect(collapse).toContain('.sidebar-resizer')
    expect(collapse).toContain('width: 44px;')
    expect(collapse).toContain('height: 44px;')
    expect(collapse).toContain('.panel-toggle-left {')
    expect(collapse).toContain('left: calc(14px + 22px) !important;')
    expect(collapse).toContain(".panel-toggle-left[aria-expanded='true'] {")
    expect(collapse).toContain('left: min(88vw, 340px) !important;')
    expect(collapse).toContain('.panel-toggle-right {')
    expect(collapse).toContain('right: calc(14px + 22px) !important;')
    expect(collapse).toContain(".panel-toggle-right[aria-expanded='true'] {")
    expect(collapse).toContain('right: min(88vw, 340px) !important;')
    expect(shell).toContain('.top-tabs-bar')
    expect(canvas).toContain('.canvas-toolbar')
    expect(appCss).toContain("@import './styles/panel-collapse.css'")
    expect(appCss).toContain("@import './styles/app-shell.css'")
    expect(appCss).toContain("@import './styles/canvas.css'")
  })

  it('defines dashboard narrow-screen reflow contracts', () => {
    const shell = read('src/dashboard/styles/shell.css')
    const metrics = read('src/dashboard/styles/metrics.css')
    const filters = read('src/dashboard/styles/filters.css')
    const tables = read('src/dashboard/styles/tables-and-tooltips.css')
    const modal = read('src/styles/result-modal-shell.css')

    expect(shell).toContain('@media (max-width: 640px)')
    expect(metrics).toContain('.dash-card-wide')
    expect(metrics).toContain('grid-template-columns: minmax(0, 1fr)')
    expect(filters).toContain('.dash-filters-grid')
    expect(tables).toContain('.dash-table-wrap')
    expect(tables).toContain('min-width: max-content')
    expect(modal).toContain('max-width: calc(100vw - 16px)')
  })

  it('defines showcase phone layout contracts', () => {
    const layout = read('src/showcase/showcase-layout.css')
    const scroll = read('src/showcase/showcase-scroll.css')
    const modal = read('src/showcase/showcase-modal.css')

    expect(layout).toContain('@media (max-width:780px)')
    expect(layout).toContain('.sc-patient-card')
    expect(layout).toContain('.sc-chart-layout')
    expect(scroll).toContain('@media (min-width: 781px)')
    expect(scroll).toContain('overscroll-behavior-x: contain')
    expect(modal).toContain('max-width: calc(100vw - 16px)')
  })
})
