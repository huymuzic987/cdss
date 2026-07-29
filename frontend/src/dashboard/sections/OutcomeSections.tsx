import type { DashboardSummaryResponse } from '../../api/types'
import { BarStat } from '../charts/BarStat'
import { LineStat } from '../charts/LineStat'
import { ordinalColor } from '../chartColors'
import { pct } from '../format'
import { SectionCard } from '../SectionCard'

export function OutcomeSections({ outcomes }: { outcomes: DashboardSummaryResponse['outcomes'] }) {
  return (
    <>
      <SectionCard
        title="Blood pressure control over time"
        subtitle="Percentage of patients at their BP goal, visit by visit"
      >
        <LineStat
          yDomain={[0, 1]}
          formatValue={(value) => pct(value as number)}
          data={outcomes.outcomes_by_visit_number.map((item) => ({ label: `Visit ${item.visit_number}`, value: item.bp_controlled_rate }))}
        />
      </SectionCard>
      <SectionCard title="Average blood pressure" subtitle="mmHg, averaged across all patients at each visit" span={2}>
        <div className="dash-chart-legend">
          <span className="dash-chart-legend-item"><span className="dash-chart-legend-swatch" style={{ background: 'var(--chart-series-1)' }} />Systolic (top number)</span>
          <span className="dash-chart-legend-item"><span className="dash-chart-legend-swatch" style={{ background: 'var(--chart-series-2)' }} />Diastolic (bottom number)</span>
        </div>
        <LineStat
          data={outcomes.outcomes_by_visit_number
            .filter((item) => item.avg_sbp !== null && item.avg_dbp !== null)
            .map((item) => ({ label: `Visit ${item.visit_number}`, sbp: item.avg_sbp as number, dbp: item.avg_dbp as number }))}
          series={[{ key: 'sbp', label: 'Systolic' }, { key: 'dbp', label: 'Diastolic' }]}
        />
      </SectionCard>
      <SectionCard title="Blood pressure goals assigned" subtitle="130/80 for higher-risk patients, 140/80 for everyone else">
        <BarStat
          data={outcomes.bp_target_distribution.map((item) => ({ label: `${item.label} mmHg`, value: item.count }))}
          colors={outcomes.bp_target_distribution.map((_, index) => ordinalColor(index))}
        />
      </SectionCard>
    </>
  )
}
