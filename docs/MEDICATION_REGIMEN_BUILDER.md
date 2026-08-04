# Medication regimen builder

`build_traversed_medication_regimen()` is the public, domain-level API for
turning medication-relevant inference nodes reached during traversal into a
stable regimen plan.

```python
from cdss.domain.decision_tree import build_traversed_medication_regimen

plan = build_traversed_medication_regimen(result, tree_repository, medicine_repository)
```

The result contains ordered `steps`, a non-flattened `effective_regimen`, and
the medicine catalog for referenced classes. `START` steps are placed first for
display, while `trace_step` preserves execution order.

## Dose rule

Every component owns its dose, route, frequency, and duration. A later `ADD`
does not inherit the dose of an earlier `START`. If a medicine or class is
mentioned without an explicit dose, its `dose_strategy` is `LOW_DOSE`.

For example:

```text
START A + C — LOW_DOSE
ADD B — USUAL_DOSE
```

remains two instructions. It is not flattened into `A + C + B — LOW_DOSE`.

## Keyword behavior

| Keyword | Regimen behavior |
|---|---|
| `START` | Establish base alternatives and display first |
| `ADD` | Add a separate component |
| `COMBINE` | Record simultaneous components without sharing dose metadata |
| `SELECT` | Preserve alternatives and mark unresolved choices |
| `ADJUST`, `CHANGE`, `ESCALATE`, `REDUCE` | Preserve an independent modification step |
| `STOP` | Record inactive components |
| `KEEP`, `MAINTAIN` | Preserve a non-destructive regimen instruction |
| `MONITOR` | Preserve medication-specific monitoring |
| `AVOID` | Record an exclusion constraint |
| `RESTORE` | Preserve an explicitly restored medication regimen |
| Other inference keywords | Remain traversal evidence unless they carry medication content |

Structured `action_payload.regimen_update` data has priority. Existing
`context_patch.treatment_preferences` data is supported directly, and catalog
text detection remains a legacy fallback.

Medication inference keys use
`T<TREE>_INFERENCE_<OPERATION>_<DOSE>_<COMPONENTS>[_<QUALIFIER>]`. `PLUS`
means simultaneous components and `OR` preserves alternatives. The payload
`operation` must match the key operation. Vietnamese display text is never
parsed for ABCD class codes.

The API response adds `presentation.regimen_plan` while continuing to emit the
legacy `medicines`, `medicine_options`, and `medicine_catalog_by_class` fields.
