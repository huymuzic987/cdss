/** Plain-language explanations for stats that aren't self-evident from their
 * label alone, shown on hover via InfoTooltip. Only the genuinely "jargon-y"
 * parameters get one -- simple counts (total patients, total visits) don't
 * need it and keep using StatTile's always-visible `hint` instead. */
export const EXPLANATIONS = {
  onSchedule:
    'Share of follow-up visits that happened on or after the date the clinician scheduled at the previous visit. Higher is better.',
  earlyReturn:
    'Share of follow-up visits that happened before the scheduled date -- usually because of side effects, worsening symptoms, or a dosing problem. Lower is generally better, but it also means a problem was caught quickly.',
  adherence:
    'Share of follow-up visits where the clinician\'s actual treatment matched what the CDSS recommended at the prior visit.',
  overdue: 'Patients whose scheduled recheck date has already passed with no new visit recorded yet.',
  effectivenessDelta:
    'The percentage-point gap in blood-pressure control between patients whose clinician followed the CDSS recommendation and those whose clinician didn\'t, measured at the next visit after an uncontrolled reading. A bigger gap means following the recommendation matters more.',
  medicationChangeRate:
    'Share of consecutive visit pairs (both with a recorded prescription) where the medication list changed from one visit to the next.',
  riskLevel:
    'Overall cardiovascular risk assigned by the CDSS, combining blood-pressure severity with other risk factors (age, comorbidities, lab values).',
  hypertensionClass:
    'Blood-pressure severity grade at the time of diagnosis, per clinical guideline thresholds (normal / high-normal / stage 1 / stage 2).',
  bpTarget:
    'The blood-pressure goal assigned to a patient: 130/80 mmHg for higher cardiovascular risk, 140/80 mmHg otherwise.',
} as const
