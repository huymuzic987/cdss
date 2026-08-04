export function cleanText(str: string): string {
  if (!str) return ''
  return str.replace(/[^\p{ASCII}]+/gu, '-').replace(/-+/g, '-').trim()
}
