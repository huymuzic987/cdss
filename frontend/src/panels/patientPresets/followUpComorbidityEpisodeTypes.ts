import type { JsonObject } from '../../api/types'

export interface EpisodeDefinition {
  slug: string
  patientId: string
  name: string
  comorbidity: JsonObject
  initialBp: [number, number]
  followUps: Array<{
    slug: string
    label: string
    description: string
    values: JsonObject
  }>
}
