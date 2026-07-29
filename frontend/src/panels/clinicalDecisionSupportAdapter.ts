import type { ExecutedAction, JsonObject, JsonValue } from '../api/types'
import type { ClinicalDecisionSupportLocale } from './clinicalDecisionSupportMessages'
import { buildClinicalSummaryEvidence, mergeEvidence, parseEvidence } from './clinicalPresentation/evidence'
import { parseOptions, parseStructuredOrders } from './clinicalPresentation/orders'
import type { ClinicalPresentation } from './clinicalPresentation/types'
import { localized, objectValue, stringValue } from './clinicalPresentation/values'

export type {
  ActionOption,
  ClinicalPresentation,
  EvidenceItem,
  RecommendedDrugClass,
  RecommendedMedicine,
  RecommendedOrder,
} from './clinicalPresentation/types'

function findPresentation(actions: ExecutedAction[]): JsonObject | null {
  for (let index = actions.length - 1; index >= 0; index -= 1) {
    const payload = actions[index].payload
    const presentation = objectValue(payload.presentation)
    if (presentation) return presentation
  }
  return null
}

function localizedText(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): string {
  const text = objectValue(value)
  return text ? localized(text, 'text', locale) : ''
}

function codedLabel(value: JsonValue | undefined, locale: ClinicalDecisionSupportLocale): string {
  const coded = objectValue(value)
  return coded ? localized(coded, 'label', locale) || stringValue(coded.code) : ''
}

export function buildClinicalPresentation(
  actions: ExecutedAction[], _input: JsonObject, context: JsonObject, locale: ClinicalDecisionSupportLocale,
): ClinicalPresentation {
  const presentation = findPresentation(actions)
  if (!presentation || presentation.schema_version !== '1.0') {
    return {
      alert: locale === 'vi' ? 'Dá»¯ liá»‡u trÃ¬nh bÃ y quyáº¿t Ä‘á»‹nh lÃ¢m sÃ ng khÃ´ng há»£p lá»‡.' : 'Invalid clinical presentation contract.',
      evidence: [], recommendation: '', orders: [], additionalActions: [],
      contractError: 'missing_or_unsupported_presentation',
    }
  }
  const structuredOrders = parseStructuredOrders(presentation.recommended_orders, locale)
  const evidence = mergeEvidence(
    buildClinicalSummaryEvidence(
      presentation, context, structuredOrders.some((order) => order.orderType === 'medication'), locale,
    ),
    parseEvidence(presentation.trigger_evidence, locale),
  )
  const lastAction = actions.at(-1)
  const recommendation = localizedText(presentation.recommendation, locale)
  return {
    alert: localizedText(presentation.alert, locale),
    evidence,
    recommendation,
    recommendationSecondary: localizedText(presentation.recommendation, locale === 'vi' ? 'en' : 'vi') || (lastAction ? (locale === 'vi' ? lastAction.text_en : lastAction.text_vi) : undefined),
    recommendationStrength: codedLabel(presentation.evidence_strength, locale),
    evidenceLevel: codedLabel(presentation.evidence_level, locale),
    orders: Array.from(new Map(structuredOrders.map((order) => [order.id, order])).values()),
    additionalActions: parseOptions(presentation.additional_actions, locale),
  }
}
