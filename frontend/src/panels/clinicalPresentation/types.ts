import type { JsonObject } from '../../api/types'

export interface RecommendedOrder {
  id: string
  name: string
  dose?: string
  classLabel?: string
  orderType?: string
  sourceData?: JsonObject
  medicineIds?: string[]
  drugClasses?: RecommendedDrugClass[]
}

export interface RecommendedMedicine {
  id: string
  name: string
  dose: string
  route?: string
  subgroup?: string
}

export interface RecommendedDrugClass {
  code: string
  label: string
  doseLabel: string
  medicines: RecommendedMedicine[]
}

export interface EvidenceItem {
  id: string
  label: string
  value: string
}

export interface ActionOption {
  id: string
  label: string
}

export interface ClinicalPresentation {
  alert: string
  evidence: EvidenceItem[]
  recommendation: string
  recommendationSecondary?: string
  recommendationStrength?: string
  evidenceLevel?: string
  orders: RecommendedOrder[]
  regimenSteps: RegimenStep[]
  regimenOptions: FinalRegimenOption[]
  additionalActions: ActionOption[]
  contractError?: string
}

export interface RegimenStep {
  id: string
  operation: string
  instruction: string
  componentLabel: string
  doseLabel: string
}

export interface FinalRegimenComponent {
  label: string
  detail: string
  group: 'A' | 'B' | 'C' | 'D' | 'MRA' | 'SGLT2i' | 'GLP1RA' | 'Others'
  dose: string
}

export interface FinalRegimenOption {
  id: string
  components: FinalRegimenComponent[]
}
