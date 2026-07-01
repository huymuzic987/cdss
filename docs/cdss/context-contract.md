# CDSS Context Contract

Status: **frozen inter-tree context contract for seeded Trees 1–5.**

The traversal engine is generic and does not interpret clinical keys. It exposes
one shared, mutable JSON object — `RunState.context` — that every tree reads from
and writes to by convention. **That object is the real API between trees.** A tree
authored later depends on the exact key names, nesting, and value domains written
by trees authored earlier. Nothing in the engine validates this shape: an
unwritten read path raises `MissingRuntimePath`, and a mis-nested write silently
produces a key no downstream tree will ever read.

This document freezes the context surface so that Tree 6 and every subsequent tree
obey a single, explicit contract instead of rediscovering it from the data.

The surface below was extracted read-only from the seeded database
(`hypertension-diagnosis`, `risk-classification`, `treatment-threshold-and-bp-target`,
`essential-treatment-strategy`, `optimal-treatment-strategy`) on 2026-07-01. No
seed or schema was changed. It is the authoritative set of context paths those
five trees actually read and write, including the literal value domains they use.

Producer/consumer legend: **T1** diagnosis, **T2** risk-classification,
**T3** treatment-threshold-and-bp-target, **T4E** essential-treatment-strategy,
**T5O** optimal-treatment-strategy.

## 1. Governance rules

1. **The context object is a contract, not a scratchpad.** Every key a tree
   writes is a public output other trees may depend on.
2. **A tree may only read a context path that some earlier tree in its execution
   path is guaranteed to have written.** If the write is conditional, the read
   must tolerate its absence (`exists` guard) or the path must be made
   unconditional. See §5 for the current load-bearing dependencies.
3. **New keys must be added to this document before they are seeded.** Adding a
   key to a tree without adding it here is a contract violation even if the tree
   works in isolation.
4. **Never rename or re-nest an existing key.** Downstream trees reference the
   exact dotted path. Renaming is a breaking change requiring a coordinated
   re-seed of every consumer and a version bump of this contract.
5. **Value domains are part of the contract.** A key documented as an enum must
   only ever be written one of its listed values. Widening a domain is a contract
   change; consumers comparing with `eq`/`in` must be updated in the same change.
6. **Keep runtime input and derived context separate.** Raw clinical inputs live
   under `input.*` and are immutable. Only engine-derived, cross-tree state
   belongs under `context.*`. Do not copy an input into context unless a
   downstream tree genuinely needs the derived form.

## 2. Namespaces

| Namespace | Owner (writer) | Purpose |
| --- | --- | --- |
| `context.diagnosis` | T1 | Diagnostic classification of the encounter. |
| `context.risk` | T2 | Cardiovascular risk stratification. |
| `context.treatment` | T3, T4E, T5O | BP target and treatment-strategy state. |
| `context.treatment_preferences` | T1 | Preferred drug-class hints. |
| `context.orchestration` | T3 | Declarative hand-off hints for parallel modifier trees. |

## 3. Key reference

### `context.diagnosis` — written by T1

| Path | Type | Allowed values | Read by | Notes |
| --- | --- | --- | --- | --- |
| `context.diagnosis.hypertension_class` | enum string | `NORMAL_BP`, `HIGH_NORMAL_BP`, `GRADE_1_HYPERTENSION`, `GRADE_2_HYPERTENSION`, `MASKED_HYPERTENSION`, `HYPERTENSIVE_EMERGENCY` | **T2** (`eq`) | **Load-bearing.** T2 branches on this exact string. Any new class value must be handled by every consumer. |
| `context.diagnosis.hypertension_phenotype` | enum string | `ISOLATED_SYSTOLIC_HYPERTENSION` | — | Output/reserved. Written on the ISH path; no current consumer. |
| `context.diagnosis.hypertension_present` | boolean | `true` | — | Output/reserved. |
| `context.diagnosis.risk_classification_group` | enum string | `GRADE_1_HYPERTENSION` | — | Output/reserved; surfaced for downstream risk logic. |

### `context.risk` — written by T2

| Path | Type | Allowed values | Read by | Notes |
| --- | --- | --- | --- | --- |
| `context.risk.level` | enum string | `LOW`, `MEDIUM`, `HIGH` | **T3, T4E, T5O** (`eq`) | **Most load-bearing key in the system.** Only T2 sets it, so any tree that reads it is only reachable through the T1→T2→T3 pipeline. Initial-encounter treatment logic depends on it. |

### `context.treatment` — written by T3 (target), T4E/T5O (status)

| Path | Type | Allowed values | Read by | Notes |
| --- | --- | --- | --- | --- |
| `context.treatment.bp_target` | object | see sub-keys | — | Container written wholesale by T3. |
| `context.treatment.bp_target.sbp.upper_exclusive_mmhg` | number | `130`, `140` | **T4E, T5O** | **Load-bearing.** 140 = generic target; 130 = comorbidity / high-risk / restore target. |
| `context.treatment.bp_target.dbp.upper_exclusive_mmhg` | number | `80` | **T4E, T5O** | **Load-bearing.** |
| `context.treatment.bp_target.sbp.lower_reference_mmhg` | number | `120` | — | Reference floor; output only. |
| `context.treatment.bp_target.sbp.or_lower` | boolean | `true` | — | Output only. |
| `context.treatment.bp_target.sbp.preferred_upper_exclusive_if_tolerated_mmhg` | number | `130` | — | Output only. |
| `context.treatment.bp_target.source` | enum string | `TREE_3_GENERIC`, `TREE_3_HIGH_NORMAL_HIGH_RISK` | — | Provenance tag for the target. |
| `context.treatment.status` | enum string | `DIFFICULT_TO_CONTROL_HYPERTENSION`, `RESISTANT_HYPERTENSION` | — | Written by T4E/T5O; **reserved for the future resistant-hypertension tree** (an anticipated consumer). |
| `context.treatment.additional_options` | array of enum strings | `["MRA","ANOTHER_DIURETIC","ALPHA_BLOCKER","BETA_BLOCKER"]` | — | Written by T5O; output only. |
| `context.treatment.pill_count` | number | `2` | — | Written by T5O; output only. |

### `context.treatment_preferences` — written by T1

| Path | Type | Allowed values | Read by | Notes |
| --- | --- | --- | --- | --- |
| `context.treatment_preferences.preferred_drug_classes` | array of enum strings | `["THIAZIDE_LIKE_DIURETIC","CALCIUM_CHANNEL_BLOCKER"]` | — | Output/reserved hint for treatment trees. |

### `context.orchestration` — written by T3

A declarative hand-off descriptor, **not** consumed by the traversal engine
itself. It documents, in data, how an orchestrator should fan a run into the
parallel modifier trees and where to resume afterward. Treat it as the seam for
the "parallel modifier trees" pattern.

| Path | Type | Value | Notes |
| --- | --- | --- | --- |
| `context.orchestration.after_parallel_modifier_trees.mode` | enum string | `SELECT_ONE_BY_INPUT` | Selection strategy after the modifier phase. |
| `context.orchestration.after_parallel_modifier_trees.input_path` | runtime path string | `input.facility_capability` | The input the selection keys on. |
| `context.orchestration.after_parallel_modifier_trees.destinations.LIMITED_RESOURCES` | tree_key | `essential-treatment-strategy` | Resume target for limited-resource facilities. |
| `context.orchestration.after_parallel_modifier_trees.destinations.FULL_RESOURCES` | tree_key | `optimal-treatment-strategy` | Resume target for full-resource facilities. |

## 4. Follow-up and medication state (currently `input`, not `context`)

Lifestyle- and medication-follow-up state is **not** currently in `context`. It
lives under immutable `input.*`:

```text
input.is_medication_follow_up        (boolean)
input.is_lifestyle_follow_up         (boolean)
input.medication_follow_up_stage     (enum string: INITIAL, ESCALATED, ...)
input.active_bp_target               (object; caller-supplied target on follow-up)
input.facility_capability            (enum string: LIMITED_RESOURCES, FULL_RESOURCES)
```

If a future tree needs to *derive* follow-up or medication state and pass it
onward (for example `context.follow_up.lifestyle_attempted`,
`context.medication.strategy`, `context.medication.phase`), those namespaces must
be reserved and documented here **before** being seeded, following §1. They do not
exist yet.

## 5. Cross-tree dependency summary (the load-bearing reads)

These are the only context reads that cross a tree boundary today. They define the
mandatory execution ordering and must never silently break:

| Consumer | Path read | Guaranteed writer | Consequence if unwritten |
| --- | --- | --- | --- |
| T2 | `context.diagnosis.hypertension_class` | T1 | `MissingRuntimePath` (T2 unreachable without T1). |
| T3, T4E, T5O | `context.risk.level` | T2 | `MissingRuntimePath`; initial-encounter treatment requires the full T1→T2→T3 path. |
| T4E, T5O | `context.treatment.bp_target.sbp.upper_exclusive_mmhg` | T3 | `MissingRuntimePath`; target-reached logic cannot evaluate. |
| T4E, T5O | `context.treatment.bp_target.dbp.upper_exclusive_mmhg` | T3 | `MissingRuntimePath`. |

Because the evaluator is non-short-circuiting, a consumer node reads these paths
whenever it is evaluated as a candidate, even in a logically dead branch. A
missing writer therefore fails the whole run, not just the branch.

## 6. Change process

1. Propose the key here (path, type, value domain, producer, consumers) before
   touching any tree.
2. Add or update the producing tree.
3. Update every consumer in the same change if a value domain widened or a read
   was added.
4. Bump the status line date and note the change.
5. Re-run the read-only extraction and the mock-patient / stress matrices to
   confirm no unwritten reads and no determinism regressions.

## 7. What the engine does and does not enforce

- The engine does **not** validate context shape, key names, or value domains.
- It only fails a specific *read* of an unwritten path (`MissingRuntimePath`) or a
  type-mismatched comparison (`InvalidRuntimeValueType`).
- Therefore a mis-nested or misspelled **write** is invisible until a consumer's
  read fails — or, worse, until a stale value from an earlier tree flows through
  unnoticed. This contract, plus the cross-tree matrix tests, is the only
  guardrail. Keep both current as trees are added.
