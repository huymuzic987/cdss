import { Toggle } from './FormControls'
import type { FormSectionProps } from './types'

export function ComorbiditiesSection({ form, setStr, setBool, disabled }: FormSectionProps) {
  return (
    <>
      <div className="ps-toggles">
        <Toggle label="Coronary Artery Disease" fieldKey="has_coronary_artery_disease" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Type 2 Diabetes" fieldKey="has_type_2_diabetes" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Diabetes (general)" fieldKey="has_diabetes" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Heart Failure" fieldKey="has_heart_failure" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Chronic Kidney Disease" fieldKey="has_ckd" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="CKD Stage 3+" fieldKey="has_ckd_stage_3_or_higher" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Cardiovascular Disease" fieldKey="has_cardiovascular_disease" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Stroke (history)" fieldKey="has_stroke" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="TIA (history)" fieldKey="has_tia" form={form} onChange={setBool} disabled={disabled} note="Transient Ischemic Attack" />
        <Toggle label="Frailty Syndrome" fieldKey="has_frailty_syndrome" form={form} onChange={setBool} disabled={disabled} />
        <Toggle label="Target Organ Damage" fieldKey="has_target_organ_damage" form={form} onChange={setBool} disabled={disabled} note="Drives the hypertensive-emergency crisis branch" />
      </div>

      {form.has_coronary_artery_disease && (
        <>
          <div className="ps-sub-label" style={{ marginTop: 8 }}>Coronary Artery Disease Detail</div>
          <div className="ps-toggles">
            <Toggle label="Acute MI / ACS" fieldKey="has_mi_acs" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="CCS Angina" fieldKey="has_ccs_angina" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="CCS Post-Revascularization" fieldKey="has_ccs_revasc" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="CABG (history)" fieldKey="has_cabg" form={form} onChange={setBool} disabled={disabled} />
          </div>
        </>
      )}

      {form.has_heart_failure && (
        <>
          <div className="ps-sub-label" style={{ marginTop: 8 }}>Heart Failure Detail</div>
          <div className="ps-toggles">
            <Toggle label="HFrEF (reduced EF)" fieldKey="has_hfref" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="HFmrEF (mildly reduced EF)" fieldKey="has_hfmref" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="HFpEF (preserved EF)" fieldKey="has_hfpef" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Left Ventricular Hypertrophy" fieldKey="has_lvh" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="BP Target Reached" fieldKey="bp_target_reached" form={form} onChange={setBool} disabled={disabled} />
          </div>
        </>
      )}

      {form.has_ckd && (
        <>
          <div className="ps-sub-label" style={{ marginTop: 8 }}>Chronic Kidney Disease Detail</div>
          <div className="ps-toggles">
            <Toggle label="Kidney Transplant (history)" fieldKey="has_kidney_transplant" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Prior Creatinine Test on File" fieldKey="has_prior_creatinine_test" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Still Using RAS Inhibitor" fieldKey="still_using_ras_inhibitor" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Creatinine Increased >30%" fieldKey="creatinine_increased_over_30_percent" form={form} onChange={setBool} disabled={disabled} />
          </div>
        </>
      )}

      {form.has_target_organ_damage && (
        <>
          <div className="ps-sub-label" style={{ marginTop: 8 }}>Hypertensive Emergency Detail</div>
          <div className="ps-toggles">
            <Toggle label="Acute Ischemic Stroke" fieldKey="has_acute_ischemic_stroke" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Thrombolysis Candidate" fieldKey="is_thrombolysis_candidate" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Acute Coronary Syndrome" fieldKey="has_acute_coronary_syndrome" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Acute Cardiogenic Pulmonary Edema" fieldKey="has_acute_cardiogenic_pulmonary_edema" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Acute Aortic Syndrome" fieldKey="has_acute_aortic_syndrome" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Eclampsia / Severe Preeclampsia / HELLP" fieldKey="has_eclampsia_severe_preeclampsia_or_hellp" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Hypertensive Encephalopathy" fieldKey="has_hypertensive_encephalopathy" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Acute Intracerebral Hemorrhage" fieldKey="has_acute_intracerebral_hemorrhage" form={form} onChange={setBool} disabled={disabled} />
          </div>
        </>
      )}

      {form.is_pregnant && (
        <>
          <div className="ps-sub-label" style={{ marginTop: 8 }}>Pregnancy Detail</div>
          <div className="ps-toggles">
            <Toggle label="Pre-Pregnancy Hypertension" fieldKey="has_pre_pregnancy_hypertension" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Hypertension Before Week 20" fieldKey="has_hypertension_before_week_20" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Hypertension After Week 20" fieldKey="has_hypertension_after_week_20" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Prior Gestational Hypertension" fieldKey="has_prior_gestational_hypertension" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="High Preeclampsia Risk" fieldKey="has_high_preeclampsia_risk" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Proteinuria" fieldKey="has_proteinuria" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Autoimmune Disease" fieldKey="has_autoimmune_disease" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Seizure" fieldKey="has_seizure" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Severe Headache" fieldKey="has_severe_headache" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Visual Disturbance" fieldKey="has_visual_disturbance" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Epigastric Pain" fieldKey="has_epigastric_pain" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Hemolysis" fieldKey="has_hemolysis" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Elevated Liver Enzymes" fieldKey="has_elevated_liver_enzymes" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Low Platelets" fieldKey="has_low_platelets" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Pulmonary Edema" fieldKey="has_pulmonary_edema" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Coagulopathy" fieldKey="has_coagulopathy" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Hypertensive Crisis" fieldKey="has_hypertensive_crisis" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Treatment Target Not Achieved" fieldKey="is_treatment_target_not_achieved" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Postpartum" fieldKey="is_postpartum" form={form} onChange={setBool} disabled={disabled} />
            <Toggle label="Breastfeeding" fieldKey="is_breastfeeding" form={form} onChange={setBool} disabled={disabled} />
          </div>
          <div className="ps-field-row" style={{ marginTop: 6 }}>
            <div className="ps-field">
              <label className="ps-field-label">Proteinuria (24h, mg)</label>
              <input
                className="ps-num-input"
                type="number" min={0}
                placeholder="e.g. 350"
                value={form.proteinuria_24h_mg}
                onChange={(e) => setStr('proteinuria_24h_mg', e.target.value)}
                disabled={disabled}
              />
            </div>
            <div className="ps-field">
              <label className="ps-field-label">ACR (mg/mmol)</label>
              <input
                className="ps-num-input"
                type="number" min={0}
                placeholder="e.g. 35"
                value={form.acr_mg_mmol}
                onChange={(e) => setStr('acr_mg_mmol', e.target.value)}
                disabled={disabled}
              />
            </div>
          </div>
          <div className="ps-field-row">
            <div className="ps-field">
              <label className="ps-field-label">Weeks Persisting Postpartum</label>
              <input
                className="ps-num-input"
                type="number" min={0}
                placeholder="e.g. 8"
                value={form.weeks_persisting_postpartum}
                onChange={(e) => setStr('weeks_persisting_postpartum', e.target.value)}
                disabled={disabled}
              />
            </div>
            <div className="ps-field">
              <label className="ps-field-label">Weeks Resolved Postpartum</label>
              <input
                className="ps-num-input"
                type="number" min={0}
                placeholder="e.g. 2"
                value={form.weeks_resolved_postpartum}
                onChange={(e) => setStr('weeks_resolved_postpartum', e.target.value)}
                disabled={disabled}
              />
            </div>
          </div>
        </>
      )}
    </>
  )
}
