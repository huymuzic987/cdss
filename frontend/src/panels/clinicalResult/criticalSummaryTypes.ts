export type ClinicalUrgency = 'immediate' | 'high' | 'moderate' | 'routine'

export interface ImportantPathStep {
  id: string
  label: string
  treeName: string
  detail?: string
  kind: 'trigger' | 'classification' | 'treatment' | 'urgent'
}

export interface FollowUpAdvice {
  timing: string
  reason: string
  source: string
}

export interface CriticalFinding {
  id: string
  label: string
  value: string
  treeName: string
}

export interface CriticalSummary {
  urgency: ClinicalUrgency
  urgencyLabel: string
  findings: CriticalFinding[]
  path: ImportantPathStep[]
  followUp: FollowUpAdvice | null
}
