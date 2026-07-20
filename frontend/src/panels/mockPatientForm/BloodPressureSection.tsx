import { BpRow } from './FormControls'
import type { FormSectionProps } from './types'

export function BloodPressureSection({ form, setStr, disabled }: FormSectionProps) {
  return (
    <>
      <div className="ps-sub-label">Initial Clinic Readings</div>
      <BpRow label="Measure 1" sbpKey="clinic_1_sbp" dbpKey="clinic_1_dbp" form={form} onChange={setStr} disabled={disabled} />
      <BpRow label="Measure 2" sbpKey="clinic_2_sbp" dbpKey="clinic_2_dbp" form={form} onChange={setStr} disabled={disabled} />
      <BpRow label="Measure 3" sbpKey="clinic_3_sbp" dbpKey="clinic_3_dbp" form={form} onChange={setStr} disabled={disabled} />

      <div className="ps-sub-label" style={{ marginTop: 8 }}>Follow-Up</div>
      <BpRow label="Pre-Lifestyle" sbpKey="pre_lifestyle_clinic_sbp" dbpKey="pre_lifestyle_clinic_dbp" form={form} onChange={setStr} disabled={disabled} />

      <div className="ps-sub-label" style={{ marginTop: 8 }}>Out-of-Office / Ambulatory</div>
      <BpRow label="Home" sbpKey="home_sbp" dbpKey="home_dbp" form={form} onChange={setStr} disabled={disabled} />
      <BpRow label="Daytime" sbpKey="daytime_sbp" dbpKey="daytime_dbp" form={form} onChange={setStr} disabled={disabled} />
      <BpRow label="Morning" sbpKey="morning_sbp" dbpKey="morning_dbp" form={form} onChange={setStr} disabled={disabled} />
      <BpRow label="24-Hour" sbpKey="bp_24h_sbp" dbpKey="bp_24h_dbp" form={form} onChange={setStr} disabled={disabled} />
    </>
  )
}
