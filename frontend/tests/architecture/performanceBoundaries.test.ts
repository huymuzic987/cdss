import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const FRONTEND_ROOT = join(process.cwd())

function read(relativePath: string): string {
  return readFileSync(join(FRONTEND_ROOT, relativePath), 'utf8')
}

describe('frontend performance boundaries', () => {
  it('keeps optional routes and the canvas out of the eager application module', () => {
    const app = read('src/App.tsx')
    const workspace = read('src/app/TreeWorkspace.tsx')

    expect(app).toMatch(/lazy\(\(\) => import\(['"]\.\/dashboard\/DashboardPage/)
    expect(app).toMatch(/lazy\(\(\) => import\(['"]\.\/showcase\/ShowcasePage/)
    expect(workspace).toMatch(/lazy\(\(\) => import\(['"]\.\.\/canvas\/TreeCanvas/)
    expect(app).not.toMatch(/import \{ DashboardPage \} from ['"]\.\/dashboard\/DashboardPage/)
    expect(app).not.toMatch(/import \{ ShowcasePage \} from ['"]\.\/showcase\/ShowcasePage/)
    expect(workspace).not.toMatch(/import \{ TreeCanvas \} from ['"]\.\.\/canvas\/TreeCanvas/)
  })

  it('loads showcase styles only with the showcase route', () => {
    expect(read('src/App.css')).not.toContain("@import './showcase/showcase.css'")
    expect(read('src/showcase/ShowcasePage.tsx')).toContain("import './showcase.css'")
  })

  it('does not pull the tldraw runtime into static side panels', () => {
    expect(read('src/panels/Legend.tsx')).not.toContain("../canvas/DecisionNodeShapeUtil")
    expect(read('src/panels/NodeDetailPanel.tsx')).not.toContain("../canvas/DecisionNodeShapeUtil")
    expect(read('src/canvas/DecisionNodeShapeUtil.tsx')).toContain("from './nodeTypeColors'")
  })

  it('caches hashed assets for repeat visits while keeping the SPA shell fresh', () => {
    const nginx = read('nginx.conf')

    expect(nginx).toContain('location = /index.html')
    expect(nginx).toContain('Cache-Control "no-cache"')
    expect(nginx).toContain('location ~* \\.(?:css|js|mjs|woff2?|svg|png|jpg|jpeg|gif|webp|ico)$')
    expect(nginx).toContain('Cache-Control "public, max-age=31536000, immutable"')
    expect(nginx).toContain('gzip_types')
  })

  it('bounds the heavy canvas dependency chunks', () => {
    const vite = read('vite.config.ts')
    expect(vite).toContain("name: 'tldraw'")
    expect(vite).toContain("name: 'elkjs'")
    expect(vite).toContain('CANVAS_CHUNK_MAX_SIZE = 450 * 1024')
    expect(vite).toContain('maxSize: CANVAS_CHUNK_MAX_SIZE')
  })

  it('loads the ELK API with a worker instead of bundling the engine', () => {
    const layout = read('src/layout/elkLayout.ts')
    expect(layout).toContain("elk-api.js")
    expect(layout).toContain("elk-worker.min.js?url")
    expect(layout).not.toContain('elk.bundled.js')
  })

  it('memoizes showcase patient cards and selection callbacks', () => {
    expect(read('src/showcase/ShowcaseChrome.tsx')).toMatch(/memo\(function PatientCard/)
    expect(read('src/showcase/ShowcasePage.tsx')).toContain('const selectPatient = useCallback(')
  })
})
