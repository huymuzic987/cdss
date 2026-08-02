# Follow-Up Flow

The CDSS handles follow-up without storing a patient checkpoint or medication
history in its own database. Every evaluation is stateless: the caller sends
the relevant episode history in the FHIR Bundle, and the backend derives the
current workflow from that request.

There are two follow-up concerns in the code:

1. **Workflow inference** determines whether the current encounter is an
   initial, lifestyle, medication, or pregnancy follow-up.
2. **Medication reassessment** decides whether an uncontrolled regimen should
   be continued, replaced at the same treatment stage, or escalated.

## General evaluation flow

`POST /evaluate` parses the Bundle into runtime input. When both previous SBP
and previous DBP are present, the evaluator:

1. Replays the previous readings through the initial hypertension tree.
2. Inspects the resulting actions and treatment context.
3. Classifies the current encounter.
4. Adds the inferred follow-up flags and state to today's runtime input.
5. Selects the appropriate tree and entry node for today's traversal.
6. Walks that tree using the current encounter data and returns its actions.

The previous traversal is used only for inference. It is not merged into the
current traversal log.

If a request does not contain complete previous BP readings, the evaluator
treats it as an initial visit and starts at the hypertension diagnosis tree.

## Follow-up classification

The previous traversal is classified with this precedence:

| Previous result | Inferred type | Current traversal |
| --- | --- | --- |
| Action supplies `next_medication_follow_up_stage` | `MEDICATION_FOLLOW_UP` | Treatment-threshold and BP-target tree |
| Follow-up action has an action type containing `LIFESTYLE` | `LIFESTYLE_FOLLOW_UP` | Treatment-threshold and BP-target tree |
| Hypertension-in-pregnancy action has `follow_up_required: true` | `PREGNANCY_FOLLOW_UP` | Pregnancy tree |
| None of the above | `INITIAL_VISIT` | Hypertension diagnosis tree |

Medication inference also restores the previous active BP target and medication
stage. A medication follow-up without a previously established BP target is
rejected as invalid input.

The public follow-up imports remain available from
`cdss.domain.follow_up`. The inference implementation is separated into
`cdss.domain.follow_up_inference` to keep responsibilities small.

## Medication reassessment decision

`evaluate_medication_follow_up` accepts a
`MedicationFollowUpAssessment`. The caller supplies the current clinic BP,
active BP target, assessment date, date the current regimen became effective,
minimum regimen duration, and three explicit clinical flags:

- whether an individual drug must be replaced;
- whether adherence is adequate;
- whether the dose is adequate.

An individual unusable or intolerable drug does **not** make its whole drug
class unusable. It is replaced with another suitable drug at the same regimen
stage. This restarts the regimen clock because the changed regimen has not yet
had its full assessment period.

The gates execute in this order:

```text
BP target reached?
├─ yes -> maintain controlled regimen; traversal may continue
└─ no
   ├─ drug replacement required?
   │  └─ yes -> replace within the same stage, reset effective date, stop
   └─ no
      ├─ minimum duration completed?
      │  └─ no -> continue unchanged until reassessment date, stop
      └─ yes
         ├─ adherence and dose adequate?
         │  └─ no -> address adherence or dose, stop
         └─ yes -> regimen may be escalated; traversal may continue
```

Both SBP and DBP must be strictly below their configured
`upper_exclusive_mmhg` limits for the target to be reached. A reading equal to
either limit is therefore uncontrolled.

Duration is calculated from `regimen_effective_date` to `assessment_date`.
The first valid reassessment date is:

```text
regimen_effective_date + minimum_regimen_days
```

The assessment date cannot precede the regimen effective date, and the minimum
duration cannot be negative.

## Medication outcomes

| Outcome | Meaning | Continue traversal? | Follow-up date behavior |
| --- | --- | ---: | --- |
| `MAINTAIN_CONTROLLED` | Current BP is controlled | Yes | No new date calculated |
| `CONTINUE_UNTIL_REASSESSMENT` | Patient returned before the unchanged regimen can be assessed | No | Keep the original calculated reassessment date |
| `REPLACE_DRUG_SAME_STAGE` | One drug must change without escalating the regimen | No | Reset effective date to today and calculate a new reassessment date |
| `ADDRESS_ADHERENCE_OR_DOSE` | Duration is sufficient, but adherence or dose is not adequate | No | No new date calculated |
| `ESCALATE_REGIMEN` | BP is uncontrolled after an adequate regimen trial | Yes | The downstream tree selects the next regimen |

`should_continue_traversal` is the boundary between the follow-up gate and the
decision tree. `false` means the follow-up decision itself is the stopping
result. `true` means the tree may proceed to its maintenance or escalation
action.

## Pregnancy follow-up

Pregnancy follow-up is also stateless. The Bundle carries the complete episode:
one Encounter is the initial visit, two is follow-up 1, three is follow-up 2,
four is follow-up 3, and later Encounters are continuing follow-up.

After pregnancy follow-up is inferred:

- a postpartum encounter resumes at `T12_C_POSTPARTUM`;
- a currently normotensive, high-preeclampsia-risk pregnancy resumes at
  `T12_C_CURRENTLY_PREGNANT`;
- an acute hypertensive pregnancy restarts at the pregnancy tree root for full
  reclassification.

The response includes pregnancy episode metadata such as episode ID, Encounter
count, follow-up number, phase, minimum-follow-up completion, and whether a next
follow-up is required. See [Pregnancy follow-up testing](pregnancy_follow_up_testing.md)
for the FHIR requirements and preset walkthrough.

## Stateless FHIR input contract

Every medication follow-up Bundle must be independently evaluable. It must
identify the patient and provide the current encounter, current clinic BP,
current regimen, active BP target, and timing/quality values needed by the
gate. The implementation does not read a saved node checkpoint or reconstruct
the regimen from an earlier request.

The flattened runtime fields used by the follow-up gate are:

| Field | Required for the gate | Meaning |
| --- | ---: | --- |
| `is_medication_follow_up` | Yes | Enables medication follow-up behavior |
| `medication_follow_up_stage` | Yes for known-stage presets | `INITIAL_REGIMEN` or `ESCALATED_REGIMEN` |
| `current_clinic_sbp`, `current_clinic_dbp` | Yes | BP measured at this encounter |
| `active_bp_target_sbp_upper`, `active_bp_target_dbp_upper` | Yes | Exclusive BP limits; converted to `active_bp_target` before traversal |
| `assessment_date` | Yes | Date of the current follow-up assessment |
| `regimen_effective_date` | Yes | Date the unchanged current regimen became effective |
| `minimum_regimen_days` | Yes | Minimum number of days before escalation can be assessed |
| `current_regimen_drug_classes` | Yes in presets | Current class combination, for example `A`, `A+D`, or `A+C+D` |
| `current_regimen_drug_count` | Preset/presentation data | Number of drugs in the current regimen |
| `drug_replacement_required` | No | One medicine is unusable and must be replaced at the same stage |
| `adherence_adequate` | No | Defaults to adequate when not reported |
| `dose_adequate` | No | Defaults to adequate when not reported |

The simulator encodes workflow values as local FHIR input extensions and the
three clinical quality flags as local clinical-flag Conditions. The canonical
FHIR parser converts them into the runtime fields above. Comorbidities remain
ordinary patient/Condition facts in the same Bundle, so after the gate permits
continuation the original tree routing still selects the relevant CKD,
diabetes, CAD, heart-failure, older-adult, or resistant-hypertension path.

## Tree traversal integration

The walker invokes `evaluate_medication_follow_up_at_bp_checkpoint` immediately
before it evaluates outgoing nodes whose keys contain `_BP_TARGET_`. The hook is
active only for medication follow-up input that supplies:

- `assessment_date` and `regimen_effective_date` as ISO dates;
- `minimum_regimen_days` as an integer;
- current clinic BP and the active BP target.

The optional flags are `drug_replacement_required`, `adherence_adequate`, and
`dose_adequate`. Existing callers that omit the scheduling fields retain the
previous tree behavior.

The input may also include `current_regimen_drug_classes` as a compact class
combination such as `A+D`, `A+C`, or `A+C+D`. The follow-up result exposes the
normalized `current_regimen_drug_classes` list and `current_regimen_label`.
Replacing an unusable individual medicine retains this class combination and
the current treatment stage; the existing tree decides which medicine within
that class is substituted. When escalation is allowed, the existing tree
continues and determines the next combination.

For `MAINTAIN_CONTROLLED` and `ESCALATE_REGIMEN`, the hook records its result in
`context.medication_follow_up` and lets the tree evaluate its existing
reached/not-reached conditions. It does not introduce or select a new branch.
For the other three outcomes, it records a terminal action and returns before
either BP condition is entered, except when a resistant-hypertension action has
just prescribed a new fourth drug as described below.

The resistant-hypertension treatment actions `T13_A_ADD_MRA`,
`T13_A_ADD_SPIRONOLACTONE`, and `T13_A_ALTERNATIVES` are explicit continuation
nodes. This allows their outgoing BP-target checkpoints to use the same gate
as the general treatment trees. The resistant flow therefore does not bypass
duration, replacement, adherence, or dose checks.

For `T13_A_ADD_MRA` or `T13_A_ADD_SPIRONOLACTONE`, an input with three current
drugs means the fourth drug is newly prescribed. Traversal stops at the add-drug
action, resets the regimen effective date to the assessment date, and returns
the next reassessment date. On a later stateless input with four current drugs,
the gate permits BP-target traversal only after the minimum regimen duration.
The traversed add-drug action remains the clinical recommendation (for example,
add low-dose spironolactone when tolerated); the gate does not append a
synthetic “continue regimen” action that would hide that recommendation.

## Result popup

The traversal popup consumes `context.medication_follow_up` and the synthetic
stop action; this is implemented rather than pending work.

- A same-stage replacement, ordinary early visit, or adherence/dose problem is added to
  Recommended Action so the reason for stopping is visible.
- A newly prescribed resistant-hypertension drug shows the traversed T13 add-drug
  action instead, while its reassessment date still comes from follow-up context.
- `MAINTAIN_CONTROLLED` adds: "Blood pressure target met. Continue monitoring
  and maintain the current regimen."
- A calculated `next_follow_up_date` is shown only as **Reassessment date**.
  The popup does not show a regimen-period explanation beside it.
- If traversal did not produce a new combination, the current regimen from
  `current_regimen_drug_classes` is still displayed in Recommended Orders.
  If traversal did produce a new combination, that new order is displayed and
  the current-regimen fallback is omitted to avoid duplication. Current-regimen
  rows keep their middle detail column empty; drug-class codes appear only in
  the class section on the right.
- Follow-up details are not added to the colored alert header or Care Setting.

## Preset episodes and expected outcomes

Each snapshot is a complete Bundle and can be selected independently; using
the same Patient ID only makes the intended chronology understandable. No
result from one preset is stored for the next preset.

| Episode | Visits after initial | Expected gate sequence |
| --- | ---: | --- |
| General review | 4 | replace, escalate, early return, controlled |
| CKD | 3 | replace, escalate, controlled |
| Type 2 diabetes | 3 | early return, controlled, maintain controlled |
| Coronary artery disease | 3 | address adherence, escalate, controlled |
| Heart failure | 3 | early return, escalate, controlled on `A+B+C+D` |
| Older adult | 3 | replace one-drug `A` regimen, escalate from `A`, controlled |
| Resistant hypertension | 6 | increase dose, replace drug, address adherence, move to three drugs, early return, uncontrolled adequate trial into resistant-HTN BP check |

In outcome names, these sequences map respectively to
`REPLACE_DRUG_SAME_STAGE`, `ESCALATE_REGIMEN`,
`CONTINUE_UNTIL_REASSESSMENT`, `MAINTAIN_CONTROLLED`, and
`ADDRESS_ADHERENCE_OR_DOSE`.

The frontend test matrix has an explicit expected outcome for every medication
episode follow-up. A coverage assertion fails if a new follow-up preset is
added without adding its expected gate result.

## Source and tests

- Follow-up public API and medication decisions:
  `src/cdss/domain/follow_up.py`
- Encounter workflow inference: `src/cdss/domain/follow_up_inference.py`
- Pregnancy episode behavior: `src/cdss/domain/pregnancy_follow_up.py`
- Evaluation integration: `src/cdss/api/routes/evaluation.py`
- BP-checkpoint hook: `src/cdss/domain/decision_tree/walker.py`
- Action continuation policy, including resistant hypertension:
  `src/cdss/domain/decision_tree/walker_policy.py`
- Result-popup follow-up presentation:
  `frontend/src/panels/TraversalResultModal.tsx` and
  `frontend/src/panels/clinicalResult/medicationFollowUpMessage.ts`
- General and comorbidity episode presets:
  `frontend/src/panels/patientPresets/followUp.ts` and
  `frontend/src/panels/patientPresets/followUpComorbidityEpisodes.ts`
- Core follow-up tests: `tests/domain/test_follow_up.py`
- Traversal-gate tests: `tests/domain/decision_tree/test_walker.py`
- Preset FHIR contract and complete outcome matrix:
  `frontend/src/panels/mockPatientForm/fhirBundle.test.ts`
- Popup presentation tests: `frontend/src/panels/TraversalResultModal.test.tsx`
- Pregnancy tests: `tests/domain/test_pregnancy_follow_up.py` and
  `tests/db/test_pregnancy_fhir_presets.py`
