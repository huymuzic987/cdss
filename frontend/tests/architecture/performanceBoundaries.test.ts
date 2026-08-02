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
})
