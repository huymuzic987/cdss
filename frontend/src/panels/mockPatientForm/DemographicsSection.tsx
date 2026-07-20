import { Toggle } from './FormControls'
import type { FormSectionProps } from './types'

export function DemographicsSection({ form, setStr, setBool, disabled }: FormSectionProps) {
  return (
    <>
      <div className="ps-field-row">
        <div className="ps-field">
          <label className="ps-field-label">Age (years)</label>
          <input
            className="ps-num-input"
            type="number" min={1} max={120}
            placeholder="e.g. 65"
            value={form.age}
            onChange={(e) => setStr('age', e.target.value)}
            disabled={disabled}
          />
        </div>
        <div className="ps-field">
          <label className="ps-field-label">
            Risk Factors
            <span className="ps-field-hint" title="Age >65, Male sex, Smoking, Elevated LDL, Obesity, HR >80, Family history CVD, Premature menopause, Prediabetes, Physical inactivity">ⓘ</span>
          </label>
          <input
            className="ps-num-input"
            type="number" min={0} max={10}
            placeholder="0 – 10"
            value={form.risk_factor_count}
            onChange={(e) => setStr('risk_factor_count', e.target.value)}
            disabled={disabled}
          />
        </div>
      </div>

      <div className="ps-toggles">
        <Toggle label="Pregnant" fieldKey="is_pregnant" form={form} onChange={setBool} disabled={disabled} />
      </div>
    </>
  )
}
