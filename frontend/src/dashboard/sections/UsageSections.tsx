import type { DashboardSummaryResponse } from '../../api/types'
import { BarStat } from '../charts/BarStat'
import { ordinalColor } from '../chartColors'
import { humanize } from '../humanize'
import { SectionCard } from '../SectionCard'

export function UsageSections({ usage }: { usage: DashboardSummaryResponse['cdss_usage'] }) {
  return (
    <>
      <SectionCard title="Where patients are treated">
        <BarStat data={usage.facility_capability_distribution.map((item) => ({ label: humanize(item.label), value: item.count }))} />
      </SectionCard>
      <SectionCard title="Severity at first diagnosis" subtitle="How serious the hypertension was when each patient was first diagnosed">
        <BarStat
          data={usage.hypertension_class_distribution.map((item) => ({ label: humanize(item.label), value: item.count }))}
          colors={usage.hypertension_class_distribution.map((_, index) => ordinalColor(index))}
        />
      </SectionCard>
      <SectionCard title="Overall cardiovascular risk" subtitle="Risk level assigned by the CDSS, combining BP severity with other risk factors">
        <BarStat
          data={usage.risk_level_distribution.map((item) => ({ label: humanize(item.label), value: item.count }))}
          colors={usage.risk_level_distribution.map((_, index) => ordinalColor(index))}
        />
      </SectionCard>
      <SectionCard title="Most common CDSS advice" subtitle="The treatment recommendations given most often across all visits">
        <BarStat
          layout="vertical"
          height={260}
          labelWidth={220}
          data={usage.recommended_action_frequency.map((item) => ({ label: item.label, value: item.count }))}
        />
      </SectionCard>
    </>
  )
}
