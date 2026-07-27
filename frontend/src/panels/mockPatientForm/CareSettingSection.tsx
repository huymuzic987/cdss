import { Toggle } from './FormControls'
import type { FormSectionProps } from './types'

export function CareSettingSection({ form, setStr, setBool, disabled }: FormSectionProps) {
  return (
    <>
      <div className="ps-field-hint" style={{ display: 'block', marginBottom: 8 }}>
        Enter both Previous Visit BP values to let the guideline infer whether today is a lifestyle or medication follow-up. Leave both empty for an initial visit.
      </div>

      <div className="ps-field" style={{ marginTop: 8 }}>
        <label className="ps-field-label">Facility Capability</label>
        <div className="ps-radio-group">
          {[
            { value: 'FULL_RESOURCES', label: 'Full Resources' },
            { value: 'LIMITED_RESOURCES', label: 'Limited Resources' },
          ].map(({ value, label }) => (
            <label key={value} className="ps-radio-label">
              <input
                type="radio"
                name="facility_capability"
                value={value}
                checked={form.facility_capability === value}
                onChange={() => setStr('facility_capability', value)}
                disabled={disabled}
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {form.facility_capability === 'LIMITED_RESOURCES' && (
        <>
          <div className="ps-sub-label" style={{ marginTop: 8 }}>Advanced Treatment Detail</div>
          <div className="ps-toggles">
            <Toggle label="Tolerates MRA" fieldKey="tolerates_mra" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Tolerates Spironolactone" fieldKey="tolerates_spironolactone" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="BP Target Reached" fieldKey="bp_target_reached" form={form} onChange={setBool} disabled={disabled} />
          </div>
        </>
      )}
    </>
  )
}
