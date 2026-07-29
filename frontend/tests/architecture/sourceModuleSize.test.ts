import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const SOURCE_ROOT = join(process.cwd(), 'src')
const SOURCE_EXTENSIONS = new Set(['.css', '.js', '.jsx', '.ts', '.tsx'])
const MAX_CODE_LINES = 200

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) return entry.name === 'test' ? [] : sourceFiles(path)
    const extension = entry.name.slice(entry.name.lastIndexOf('.'))
    return SOURCE_EXTENSIONS.has(extension) ? [path] : []
  })
}

function isExcluded(path: string): boolean {
  return path.endsWith('types.ts')
    || path.includes('.test.')
    || path.includes('.generated.')
    || path.includes(`${join('src', 'schemas')}`)
    || path.includes(`${join('src', 'models')}`)
}

function codeLineCount(path: string): number {
  return readFileSync(path, 'utf8').split(/\r?\n/).filter((line) => {
    const content = line.trim()
    return content !== ''
      && !content.startsWith('//')
      && !content.startsWith('/*')
      && !content.startsWith('*')
      && !content.startsWith('*/')
  }).length
}

describe('frontend source module size', () => {
  it(`keeps handwritten behavior and style modules at or below ${MAX_CODE_LINES} code lines`, () => {
    const oversized = sourceFiles(SOURCE_ROOT)
      .filter((path) => !isExcluded(path))
      .map((path) => ({ path, lines: codeLineCount(path) }))
      .filter(({ lines }) => lines > MAX_CODE_LINES)
      .map(({ path, lines }) => `${path.slice(SOURCE_ROOT.length + 1)}: ${lines}`)

    expect(oversized, `Oversized frontend modules:\n${oversized.join('\n')}`).toEqual([])
  })
})
