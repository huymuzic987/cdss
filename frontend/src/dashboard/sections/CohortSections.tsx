import type { DashboardSummaryResponse } from '../../api/types'
import { BarStat } from '../charts/BarStat'
import { DonutStat } from '../charts/DonutStat'
import { flatColors, ordinalColor, SECTION_COLORS } from '../chartColors'
import { compact, pct } from '../format'
import { humanize } from '../humanize'
import { SectionCard } from '../SectionCard'

interface CohortSectionsProps {
  overview: DashboardSummaryResponse['overview']
  outcomes?: DashboardSummaryResponse['outcomes']
  efficacy: DashboardSummaryResponse['efficacy']
  usage?: DashboardSummaryResponse['cdss_usage']
}

export function CohortSections({ overview, outcomes, efficacy, usage }: CohortSectionsProps) {
  return (
    <>
      <SectionCard
        title="Comorbidities (by ICD-10)"
        subtitle="Share of patients who also have each condition, alongside hypertension — I10 excluded since every patient has it"
      >
        <BarStat
          layout="vertical"
          formatValue={compact}
          data={overview.comorbidity_prevalence.map((row) => ({ label: humanize(row.label), value: row.count }))}
          colors={flatColors(SECTION_COLORS.comorbidities, overview.comorbidity_prevalence.length)}
        />
        <div className="dash-table-wrap" style={{ marginTop: 10 }}>
          <table className="dash-table">
            <thead><tr><th>ICD-10</th><th>Condition</th><th>Patients</th></tr></thead>
            <tbody>{overview.comorbidity_prevalence.map((row) => (
              <tr key={row.label}><td>{row.label}</td><td>{humanize(row.label)}</td><td>{row.count}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </SectionCard>
      {outcomes && (
        <SectionCard title="Blood pressure levels (SBP)" subtitle="Every visit's systolic reading, bucketed by severity">
          <BarStat
            layout="vertical"
            data={outcomes.sbp_severity_distribution.map((item) => ({ label: item.label, value: item.count }))}
            colors={outcomes.sbp_severity_distribution.map((_, index) => ordinalColor(index))}
          />
        </SectionCard>
      )}
      <SectionCard
        title="Risk factor count"
        subtitle="How many tracked risk factors each patient has"
      >
        <BarStat
          data={overview.risk_factor_distribution.map((item) => ({ label: item.label, value: item.count }))}
          colors={flatColors(SECTION_COLORS.riskFactorCount, overview.risk_factor_distribution.length)}
        />
      </SectionCard>
      <SectionCard title="Age distribution" subtitle="How the patient population is spread across age bands">
        <BarStat
          data={overview.age_distribution.map((item) => ({ label: item.label, value: item.count }))}
          colors={flatColors(SECTION_COLORS.age, overview.age_distribution.length)}
          showValueLabels
        />
      </SectionCard>
      <SectionCard title="CDSS adherence" subtitle="Share of flagged visits where the clinician followed the CDSS recommendation">
        <DonutStat
          centerLabel={pct(efficacy.overall_adherence_rate)}
          slices={[
            { label: 'Followed advice', value: efficacy.adherent_visit_count, color: SECTION_COLORS.adherenceYes },
            { label: "Didn't follow", value: efficacy.non_adherent_visit_count, color: SECTION_COLORS.adherenceNo },
          ]}
        />
      </SectionCard>
      {usage && (
        <SectionCard title="Antihypertensive drug classes" subtitle="Medication records grouped by class across all visits" span={2}>
          <BarStat
            layout="vertical"
            height={200}
            labelWidth={200}
            data={usage.drug_class_distribution.map((item) => ({ label: item.label, value: item.count }))}
            colors={flatColors(SECTION_COLORS.drugClasses, usage.drug_class_distribution.length)}
            showValueLabels
          />
        </SectionCard>
      )}
      <SectionCard title="Patients by gender">
        <BarStat data={overview.gender_distribution.map((item) => ({ label: humanize(item.label), value: item.count }))} />
      </SectionCard>
    </>
  )
}
