import { BpRow } from './FormControls'
import type { FormSectionProps } from './types'

export function BloodPressureSection({ form, setStr, disabled }: FormSectionProps) {
  return (
    <>
      <div className="ps-sub-label">Clinic Reading</div>
      <BpRow label="Current" sbpKey="current_clinic_sbp" dbpKey="current_clinic_dbp" form={form} onChange={setStr} disabled={disabled} />

      <div className="ps-sub-label" style={{ marginTop: 8 }}>Follow-Up</div>
      <BpRow label="Previous Visit" sbpKey="previous_sbp" dbpKey="previous_dbp" form={form} onChange={setStr} disabled={disabled} />
      <BpRow label="Previous Target" sbpKey="previous_target_sbp" dbpKey="previous_target_dbp" form={form} onChange={setStr} disabled={disabled} />

      <div className="ps-sub-label" style={{ marginTop: 8 }}>Home (Pregnancy Classification)</div>
      <BpRow label="Home" sbpKey="home_sbp" dbpKey="home_dbp" form={form} onChange={setStr} disabled={disabled} />
    </>
  )
}
