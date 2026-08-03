export function cleanText(str: string): string {
  if (!str) return ''
  return str.replace(/[^\x00-\x7F]+/g, '-').replace(/-+/g, '-').trim()
}
