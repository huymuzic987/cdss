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
either BP condition is entered.

The frontend follow-up presets include five chronological snapshots using the
same Patient ID, `medication-follow-up-review-001`: initial two-drug treatment,
same-stage replacement of one unusable drug, escalation to three drugs after
28 days, an early unchanged visit, and target reached on the scheduled
reassessment date. These remain stateless requests; selecting them in order
does not persist earlier results.

### Traversal popup requirement

The traversal popup still needs a presentation update for follow-up stops. When
the gate returns `REPLACE_DRUG_SAME_STAGE`, `CONTINUE_UNTIL_REASSESSMENT`, or
`ADDRESS_ADHERENCE_OR_DOSE`, the popup should explain why traversal stopped at
that checkpoint instead of making the stop look like an incomplete tree run.
It should display the follow-up outcome, the checkpoint node, regimen effective
date, next follow-up date when present, BP-target result, and whether minimum
duration was completed. The data already exists in
`context.medication_follow_up` and in the synthetic stop action payload; this is
a frontend presentation task and must not change traversal branching.

## Source and tests

- Follow-up public API and medication decisions:
  `src/cdss/domain/follow_up.py`
- Encounter workflow inference: `src/cdss/domain/follow_up_inference.py`
- Pregnancy episode behavior: `src/cdss/domain/pregnancy_follow_up.py`
- Evaluation integration: `src/cdss/api/routes/evaluation.py`
- BP-checkpoint hook: `src/cdss/domain/decision_tree/walker.py`
- Core follow-up tests: `tests/domain/test_follow_up.py`
- Traversal-gate tests: `tests/domain/decision_tree/test_walker.py`
- Pregnancy tests: `tests/domain/test_pregnancy_follow_up.py` and
  `tests/db/test_pregnancy_fhir_presets.py`
