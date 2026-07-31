import type { JsonObject, JsonValue } from '../../api/types'
import type { ClinicalDecisionSupportLocale } from '../clinicalDecisionSupportMessages'
import { readableIdentifier } from './decisionPath'
import type { CriticalSummary } from './criticalSummaryTypes'

export function formatEvaluation(details: JsonObject | null | undefined): string | undefined {
  if (!details) return undefined
  if (details.kind === 'comparison') {
    const left = object(details.left), right = object(details.right)
    const value = primitive(left?.value), expected = primitive(right?.value)
    const path = typeof left?.path === 'string' ? readableClinicalPath(left.path) : ''
    const operators: Record<string, string> = { eq: '=', gt: '>', gte: '≥', lt: '<', lte: '≤', in: '∈' }
    if (path && value !== undefined && expected !== undefined) {
      if (details.operator === 'eq') {
        return typeof value === 'boolean' ? path : `${path}: ${displayValue(value)}`
      }
      return `${path}: ${displayValue(value)} ${operators[String(details.operator)] ?? ''} ${displayValue(expected)}`.trim()
    }
  }
  const children = Array.isArray(details.children) ? details.children : []
  const matches = children.flatMap((child) => {
    const item = object(child)
    return item?.result === true ? [formatEvaluation(item)] : []
  }).filter((value): value is string => Boolean(value))
  return matches.slice(0, 2).join('; ') || undefined
}

export function uniqueFindings(findings: CriticalSummary['findings']): CriticalSummary['findings'] {
  const seen = new Set<string>()
  return findings.filter((finding) => {
    const key = `${finding.label}:${finding.value}`.toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export function confirmedText(locale: ClinicalDecisionSupportLocale): string {
  return locale === 'vi' ? 'Đã xác nhận trong quá trình đánh giá' : 'Confirmed during clinical assessment'
}

export function formatVisitDate(value: string, locale: ClinicalDecisionSupportLocale): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale === 'vi' ? 'vi-VN' : 'en-GB', {
    year: 'numeric', month: 'short', day: 'numeric',
  }).format(date)
}

function displayValue(value: string | number | boolean): string | number {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return typeof value === 'string' ? readableIdentifier(value) : value
}

function readableClinicalPath(path: string): string {
  const key = path.split('.').at(-1) ?? path
  const labels: Record<string, string> = {
    current_clinic_sbp: 'Clinic SBP', current_clinic_dbp: 'Clinic DBP',
    home_sbp: 'Home SBP', home_dbp: 'Home DBP',
    gestational_age_weeks: 'Gestational age', follow_up_number: 'Follow-up number',
    level: 'Risk level',
  }
  return labels[key] ?? readableIdentifier(key)
}

function object(value: JsonValue | undefined): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value : null
}

function primitive(value: JsonValue | undefined): string | number | boolean | undefined {
  return ['string', 'number', 'boolean'].includes(typeof value)
    ? value as string | number | boolean
    : undefined
}
