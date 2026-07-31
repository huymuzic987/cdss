import { useState } from 'react'

export type EmergencyScenarioFlags = Record<string, boolean>

interface Props { onConfirm: (flags: EmergencyScenarioFlags) => void; onCancel: () => void }

const SCENARIOS = [
  ['has_hypertensive_encephalopathy', 'Hypertensive encephalopathy'],
  ['has_acute_ischemic_stroke', 'Acute ischemic stroke'],
  ['is_thrombolysis_candidate', 'Thrombolysis candidate'],
  ['has_acute_intracerebral_hemorrhage', 'Acute intracerebral hemorrhage'],
  ['has_acute_coronary_syndrome', 'Acute coronary syndrome'],
  ['has_acute_cardiogenic_pulmonary_edema', 'Cardiogenic pulmonary edema'],
  ['has_acute_aortic_syndrome', 'Acute aortic syndrome'],
  ['has_eclampsia_severe_preeclampsia_or_hellp', 'Eclampsia / severe preeclampsia / HELLP'],
] as const

export function EmergencyScenarioCheckbox({ onConfirm, onCancel }: Props) {
  const [selected, setSelected] = useState<EmergencyScenarioFlags>({})
  const toggle = (key: string) => setSelected((current) => ({ ...current, [key]: !current[key] }))
  const canConfirm = Object.values(selected).some(Boolean)
  return (
    <div className="dtc-overlay" onClick={onCancel}>
      <div className="dtc-box esc-box" onClick={(event) => event.stopPropagation()}>
        <div className="dtc-header"><div className="dtc-header-icon">!</div><div>
          <div className="dtc-header-title">Determine target-organ scenario</div>
          <div className="dtc-header-sub">Select every acute emergency finding that is present.</div>
        </div></div>
        <div className="dtc-body esc-body">
          {SCENARIOS.map(([key, label]) => (
            <label className={`esc-choice${selected[key] ? ' active' : ''}`} key={key}>
              <input type="checkbox" checked={selected[key] === true} onChange={() => toggle(key)} />
              <span>{label}</span>
            </label>
          ))}
        </div>
        <div className="dtc-footer"><div className="dtc-summary">
          {canConfirm ? 'Selections will be evaluated through the emergency pathway.' : 'Select at least one finding to continue.'}
        </div><div className="dtc-footer-actions">
          <button type="button" className="dtc-btn-cancel" onClick={onCancel}>Cancel</button>
          <button type="button" className={`dtc-btn-confirm${canConfirm ? '' : ' disabled'}`} disabled={!canConfirm} onClick={() => onConfirm(selected)}>Confirm & Continue</button>
        </div></div>
      </div>
    </div>
  )
}
