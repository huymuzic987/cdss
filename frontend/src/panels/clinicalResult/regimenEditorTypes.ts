export type DragSelection = {
  selectorKind: 'group' | 'subgroup' | 'medicine'
  groupCode: string
  subgroup?: string
  medicineId?: string
}

export type DragPayload = DragSelection & {
  source: 'catalog' | 'row'
  optionId?: string
  componentIndex?: number
}

export function catalogDragData(selection: DragSelection): string {
  return JSON.stringify({ source: 'catalog', ...selection })
}

export function parseDragData(value: string): DragPayload | null {
  try {
    const parsed = JSON.parse(value) as DragSelection & { source?: string, optionId?: string, componentIndex?: number }
    if (parsed.source === 'catalog' || parsed.source === 'row') return parsed as DragPayload
  } catch {
    // Ignore malformed drag payloads.
  }
  return null
}
