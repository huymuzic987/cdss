import { Toggle } from './FormControls'
import type { FormSectionProps } from './types'

export function CareSettingSection({ form, setStr, setBool, disabled }: FormSectionProps) {
  return (
    <>
      {/* Active BP Target — kept up top since it drives the follow-up comparison below */}
      <div className="ps-toggles">
        <Toggle label="Has Active BP Target" fieldKey="has_active_bp_target" form={form} onChange={setBool} disabled={disabled} note="Patient already on therapy" />
      </div>

      {form.has_active_bp_target && (
        <div className="ps-bp-target-box">
          <div className="ps-field-hint" style={{ display: 'block', marginBottom: 6 }}>
            Target is reached when SBP is below the SBP target AND DBP is below the DBP target.
          </div>
          <div className="ps-field-row">
            <div className="ps-field">
              <label className="ps-field-label">SBP Target (mmHg)</label>
              <input
                className="ps-num-input"
                type="number" min={60} max={200}
                placeholder="e.g. 140"
                value={form.target_sbp_upper}
                onChange={(e) => setStr('target_sbp_upper', e.target.value)}
                disabled={disabled}
              />
            </div>
            <div className="ps-field">
              <label className="ps-field-label">DBP Target (mmHg)</label>
              <input
                className="ps-num-input"
                type="number" min={40} max={120}
                placeholder="e.g. 80"
                value={form.target_dbp_upper}
                onChange={(e) => setStr('target_dbp_upper', e.target.value)}
                disabled={disabled}
              />
            </div>
          </div>
        </div>
      )}


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

      <div className="ps-toggles" style={{ marginTop: 8 }}>
        <Toggle label="Lifestyle Follow-Up Visit" fieldKey="is_lifestyle_follow_up" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Medication Follow-Up Visit" fieldKey="is_medication_follow_up" form={form} onChange={setBool} disabled={disabled} />
      </div>

      {form.is_medication_follow_up && (
        <div className="ps-field" style={{ marginTop: 8 }}>
          <label className="ps-field-label">Medication Follow-Up Stage</label>
          <div className="ps-radio-group">
            {[
              { value: 'INITIAL_REGIMEN', label: 'Initial Regimen' },
              { value: 'ESCALATED_REGIMEN', label: 'Escalated Regimen' },
            ].map(({ value, label }) => (
              <label key={value} className="ps-radio-label">
                <input
                  type="radio"
                  name="medication_follow_up_stage"
                  value={value}
                  checked={form.medication_follow_up_stage === value}
                  onChange={() => setStr('medication_follow_up_stage', value)}
                  disabled={disabled}
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      )}

      {form.is_medication_follow_up && form.medication_follow_up_stage === 'ESCALATED_REGIMEN' && form.facility_capability === 'LIMITED_RESOURCES' && (
        <>
          <div className="ps-sub-label" style={{ marginTop: 8 }}>Resistant Hypertension Detail (Limited Resources)</div>
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
