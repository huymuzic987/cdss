import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { cleanText } from './cleanText'

describe('cleanText', () => {
  it('preserves ASCII text and trims it', () => {
    expect(cleanText('  Blood pressure  ')).toBe('Blood pressure')
  })

  it('replaces non-ASCII runs and collapses repeated separators', () => {
    expect(cleanText('  Tăng huyết áp —— urgent  ')).toBe('T-ng huy-t -p - urgent')
  })

  it('returns an empty string for empty input', () => {
    expect(cleanText('')).toBe('')
  })

  it('uses a Unicode property escape for the ASCII range', () => {
    const source = readFileSync('src/utils/cleanText.ts', 'utf8')
    expect(source).toContain('[^\\p{ASCII}]')
    expect(source).not.toContain('[^\\x00-\\x7F]')
  })
})
