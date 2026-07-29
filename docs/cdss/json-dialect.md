# Decision-Tree JSON Dialect

Status: audited runtime dialect. This document was first audited against the
first five seeded trees on 2026-06-29; it has since been re-checked against
the full 14-tree seed set committed at `backups/cdss_prod_20260724.sql` and
against the parsing/validation code in `src/cdss/domain/decision_tree/`
(`conditions.py`, `patches.py`, `paths.py`, `validator.py`). The dialect rules
below did not change between audits - only the tree count and row counts did.

## 1. Audit evidence

The seeded database now contains 14 decision trees (see
`backups/README.md` and `docs/database.md`):

```text
hypertension-diagnosis
risk-classification
treatment-threshold-and-bp-target
essential-treatment-strategy
optimal-treatment-strategy
hypertension-type-2-diabetes
drug-combination
hypertension-chronic-kidney-disease
hypertension-in-pregnancy
hypertensive-emergency
resistant-hypertension
hypertension-heart-failure
hypertension-coronary-artery-disease
hypertension-older-adults
```

`hypertension-older-adults` is a LINK target referenced by other trees but is
**not itself seeded**: traversing into it raises a typed `LinkTargetNotFound`
(see [traversal-engine-contract.md](traversal-engine-contract.md)). The other
13 are fully seeded and traversable.

Counted directly from the committed snapshot `backups/cdss_prod_20260724.sql`
(the `decision_nodes` table), across all 14 trees: 420 nodes, 465 internal
edges, 331 source references. By node type: 14 `START`, 181 `CONDITION`, 86
`INFERENCE`, 45 `ACTION`, 26 `END`, 55 `LINK`, 13 `GLOBAL`. Of those nodes:

- 197 non-null `condition_definition` values (including 16 of the 55 `LINK`
  nodes, which carry a condition when they are one of several outgoing branch
  candidates - see `drug-combination`'s facility/comorbidity routing);
- 74 non-null `context_patch` values;
- 84 non-null `action_payload` values; and
- 13 non-null `global_config` values (one per `GLOBAL` node).

No seed data or schema was changed to produce these counts. The dialect shapes
documented below (operators, nesting, arithmetic, patch semantics) were
verified against the current parsing/validation code, which is unchanged
since the original five-tree audit - the frozen dialect is the same, only the
seeded data has grown.

## 2. JSONB columns

`decision_nodes` contains four nullable JSONB columns:

| Column | Runtime meaning |
| --- | --- |
| `condition_definition` | Boolean expression used while a node is an outgoing candidate. |
| `context_patch` | Static recursive merge and/or ordered context operations on node entry. |
| `action_payload` | Opaque action data copied into the result. |
| `global_config` | Opaque tree-level configuration exposed as metadata from GLOBAL nodes. |

`node_source_references.section_path` is also JSONB, but it is evidence metadata,
not part of the condition/patch dialect. The audited values are ordered arrays
of section objects containing `number` and `title`.

All engine-recognized documents must be JSON objects. JSON arrays appear only
at defined child/operation positions. Unknown expression or operation keys are
configuration errors, not extension points.

## 3. Runtime paths

The only valid path roots are:

```text
input.
context.
```

Examples required by the project contract:

```text
input.current_clinic_sbp
input.is_medication_follow_up
input.active_bp_target
input.clinic_1_sbp
input.facility_capability
context.risk.level
context.treatment.bp_target
context.treatment.bp_target.sbp.upper_exclusive_mmhg
```

Path segments traverse JSON objects by exact key. Missing paths raise a typed
error when evaluated or required by a patch, except for the explicit `exists`
operator. There is no fallback value, string coercion, array-index syntax,
wildcard, or implicit root.

## 4. Condition definitions

A condition definition is one of:

```text
all expression
any expression
not expression
comparison expression
```

The forms are mutually exclusive at each expression object.

### 4.1 `all`

```json
{
  "all": [
    {
      "path": "input.current_clinic_sbp",
      "op": "gte",
      "value": 140
    },
    {
      "path": "input.current_clinic_dbp",
      "op": "gte",
      "value": 90
    }
  ]
}
```

`all` contains a non-empty ordered array of condition definitions. Every child
must evaluate to true.

The shapes, paths, and thresholds in this document were checked against the
audited seed rows.

### 4.2 `any`

```json
{
  "any": [
    {
      "path": "input.current_clinic_sbp",
      "op": "gte",
      "value": 180
    },
    {
      "path": "input.current_clinic_dbp",
      "op": "gte",
      "value": 120
    }
  ]
}
```

`any` contains a non-empty ordered array of condition definitions. At least one
child must evaluate to true.

### 4.3 `not`

```json
{
  "not": {
    "path": "input.is_medication_follow_up",
    "op": "eq",
    "value": true
  }
}
```

`not` contains exactly one condition definition and negates its result.

### 4.4 Nesting

`all`, `any`, and `not` may contain each other recursively:

```json
{
  "all": [
    {
      "path": "input.is_medication_follow_up",
      "op": "eq",
      "value": true
    },
    {
      "not": {
        "any": [
          {
            "path": "input.current_clinic_sbp",
            "op": "lt",
            "value": 90
          },
          {
            "path": "input.current_clinic_dbp",
            "op": "lt",
            "value": 60
          }
        ]
      }
    }
  ]
}
```

Evaluation details must preserve child ordering and individual results for
trace logging.

## 5. Comparison expressions

### 5.1 Static right-hand value

```json
{
  "path": "input.current_clinic_sbp",
  "op": "gte",
  "value": 140
}
```

This resolves the left operand from `path` and compares it with the literal
JSON value in `value`.

### 5.2 Dynamic right-hand value

```json
{
  "path": "input.current_clinic_sbp",
  "op": "lt",
  "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"
}
```

`value_from_path` resolves the right operand at runtime. A comparison must
contain exactly one of `value` and `value_from_path`.

### 5.3 Subtraction left-hand expression

```json
{
  "left": {
    "expression": "subtract",
    "left_path": "input.previous_clinic_sbp",
    "right_path": "input.current_clinic_sbp"
  },
  "op": "gte",
  "value": 10
}
```

The expression means:

```text
resolve(left_path) - resolve(right_path)
```

Both operands must be numeric and neither may be a boolean. The subtraction
result becomes the left operand of the comparison.

`left.expression` supports only `subtract`. `left_path` and `right_path` are
both required. A subtraction comparison uses `left` instead of top-level
`path`; supplying both is malformed.

The right comparison operand follows the same exclusive `value` or
`value_from_path` rule.

### 5.4 Path existence

The exact two-key form tests whether a path is present at all:

```json
{
  "op": "exists",
  "path": "input.clinic_1_sbp"
}
```

`exists` returns true when the exact path is present, including when its value
is JSON null. A missing segment returns false for this operator only. It has no
`value` or `value_from_path` operand. Invalid path syntax or roots remain
configuration errors.

### 5.5 Literal membership

Seeded Tree 2 uses literal-array membership:

```json
{
  "op": "in",
  "path": "input.risk_factor_count",
  "value": [1, 2]
}
```

Membership uses the same strict equality as `eq`; booleans therefore do not
match numeric `0` or `1`. The audited form requires a literal JSON array and
does not accept `value_from_path`.

## 6. Operators and strict types

The frozen operator set is:

```text
eq
exists
in
lt
lte
gt
gte
```

Semantics:

| Operator | Meaning |
| --- | --- |
| `eq` | Strict equality without string/number coercion. |
| `exists` | Whether an exact runtime path is present. |
| `in` | Strict membership in a literal JSON array. |
| `lt` | Numeric left operand is less than numeric right operand. |
| `lte` | Numeric left operand is less than or equal to numeric right operand. |
| `gt` | Numeric left operand is greater than numeric right operand. |
| `gte` | Numeric left operand is greater than or equal to numeric right operand. |

Rules:

- `lt`, `lte`, `gt`, and `gte` require numeric operands.
- JSON booleans are not numeric, even though Python's `bool` subclasses `int`.
- Numeric strings such as `"140"` are not coerced.
- Missing paths raise `MissingRuntimePath`, except that an `exists` check
  returns false.
- Wrong operand types raise `InvalidRuntimeValueType`.
- Unknown operators raise `UnsupportedOperator`.
- Null or malformed condition documents raise
  `InvalidConditionDefinition`.
- A `CONDITION` node must have a non-null condition definition.
- A non-`CONDITION` candidate with no condition definition is unconditional.

## 7. Context patches

Context patches support static recursive merge, ordered operations, or both in
one object.

### 7.1 Static deep merge

```json
{
  "diagnosis": {
    "hypertension_class": "NORMAL_BP"
  }
}
```

Normal top-level keys are recursively merged into `RunState.context`.

Rules:

- Objects merge recursively.
- Non-object values replace the existing value at the same path.
- Arrays are values and replace rather than merge element by element.
- Overwriting an existing value is valid.
- Every changed or overwritten `context.` path is recorded.
- Patch values are deep-copied.
- Static keys are interpreted relative to the context root; they do not include
  a top-level `context` wrapper.

### 7.2 Ordered operations

```json
{
  "operations": [
    {
      "op": "COPY_PATH",
      "from_path": "input.active_bp_target",
      "to_path": "context.treatment.bp_target",
      "required": true
    }
  ]
}
```

Processing order is:

1. Deep-merge every normal key except `operations`.
2. Execute operations in listed array order.

`COPY_PATH` rules:

- `from_path` starts with `input.` or `context.`.
- `to_path` starts with `context.`.
- The resolved value is deep-copied before assignment.
- Existing target values may be overwritten and are recorded as changed.
- `required: true` with a missing source raises `ContextPatchError`.
- An unsupported operation or malformed operation raises
  `ContextPatchError`.
- No operation may write to `input_snapshot`.

The behavior of a missing source with `required: false` is a no-op.

### 7.3 Combined patch

```json
{
  "treatment": {
    "follow_up_mode": "medication"
  },
  "operations": [
    {
      "op": "COPY_PATH",
      "from_path": "input.active_bp_target",
      "to_path": "context.treatment.bp_target",
      "required": true
    }
  ]
}
```

The static `treatment.follow_up_mode` merge happens before the copy operation.

## 8. Action payloads

`action_payload` is a non-null JSON object when a node emits structured output.
It is deliberately opaque to the generic engine:

```json
{
  "... seed-defined keys ...": "... seed-defined values ..."
}
```

The engine deep-copies and preserves the entire payload together with source
tree/node metadata. It must not branch on action keys or translate clinical
content - with one narrow, explicit exception (see below).

Across the 14-tree seed, `action_type` values include
`CONTINUE_LIFESTYLE_AND_MONITORING`, `LIFESTYLE_AND_CONTINUED_MONITORING`,
`MAINTAIN_CURRENT_REGIMEN`, `CONTINUE_MONITORING`,
`CONTINUE_MONITORING_AND_MAINTAIN_REGIMEN`,
`FIXED_DOSE_THREE_DRUG_COMBINATION`, `ASPIRIN_PROPHYLAXIS`, and other
treatment-selection actions. Common fields include follow-up mode/requirement,
next follow-up stage, pill count, drug classes/options, and clinician-review
flags.

The text `Tiếp tục theo dõi và duy trì phác đồ` is stored in `text_vi` on
several trees' END nodes; their structured action payloads are collected
unchanged.

### 8.1 Medicine-catalog enrichment (the one exception)

`collect_action()` in `src/cdss/domain/decision_tree/actions.py` recognizes a
fixed, small set of `action_type` values on `END` nodes and, only for those,
adds extra keys to the payload after copying it:

- If `action_type` is one of `CONSIDER_MONOTHERAPY`,
  `INITIAL_TWO_DRUG_COMBINATION`, or
  `INCREASE_DOSE_OR_THREE_DRUG_COMBINATION`, it reads
  `context.treatment_preferences.combination_options` /
  `.escalation_options` / `.additional_drug_classes` (an A/B/C/D drug-class
  letter scheme written by `drug-combination`'s `INFERENCE` nodes) and adds a
  `medicine_options` array, each entry resolved to actual oral, available
  medicines from the `medicines` table via the injected `MedicineRepository`.
- If `action_type` is `ASPIRIN_PROPHYLAXIS` (the `hypertension-in-pregnancy`
  tree's aspirin END node), it adds a `medicines` array naming that one
  specific drug by `drug_id`, unfiltered by route/availability.

This is not part of the JSON dialect itself - `action_payload` as stored in
the database never contains `medicine_options`/`medicines`; those keys exist
only in the API response, added at traversal time. It is documented here
because it is the one place the generic engine reads an `action_type` value
at all. See `src/cdss/domain/decision_tree/drug_classes.py` for the resolution
logic and `docs/database.md` for the `medicines` table.

## 9. Global configuration

`global_config` is a JSON object attached to `GLOBAL` nodes. The generic engine:

- preserves it as stored;
- exposes it through `TreeMetadata`;
- orders multiple GLOBAL nodes deterministically by `display_order`;
- does not enter GLOBAL nodes;
- does not automatically merge it into runtime context; and
- does not interpret clinical keys.

The five audited GLOBAL configurations contain metadata for age-threshold
notes, risk-classification behavior, BP-target restoration, and BP-target
comparison/override contracts. They include runtime path strings but remain
opaque metadata and are not merged into context.

## 10. Link fields are not JSON dialect

Cross-tree links use scalar columns:

```text
link_target_tree_key
link_target_node_key
```

They are not encoded in a JSONB payload. A LINK may independently carry a
`condition_definition` (55 `LINK` nodes exist across the seed; 16 of them
carry a condition because they are one of several outgoing branch candidates,
for example `treatment-threshold-and-bp-target`'s facility/comorbidity routing).

At the original five-tree audit, `hypertensive-emergency`,
`hypertension-heart-failure`, `hypertension-coronary-artery-disease`,
`hypertension-type-2-diabetes`, `hypertension-chronic-kidney-disease`,
`drug-combination`, and `resistant-hypertension` were unseeded LINK targets.
As of the current 14-tree seed, **all of those are now seeded** (see §1).
**`hypertension-older-adults` remains the one unseeded LINK target**: see
`docs/cdss/mock-patient-test-matrix.md` for the fixture that exercises it.
Traversing into it must produce a typed `LinkTargetNotFound`, not terminal
success.

## 11. Audited shape summary

- Conditions use `all`, `any`, `not`, comparisons, and subtraction
  expressions.
- Observed operators are `eq`, `exists`, `gte`, `in`, `lt`, and `lte`; `gt`
  remains supported by the frozen engine contract.
- The only condition object without a right operand is `exists`.
- The ordered patch operation supported is `COPY_PATH`; the canonical example
  is required `COPY_PATH` from `input.active_bp_target` to
  `context.treatment.bp_target`, used by `treatment-threshold-and-bp-target`.
- Source-reference `section_path` values are ordered JSON arrays of objects
  carrying section `number` and `title` fields.
- Across the 14-tree seed: 197 nodes carry a `condition_definition` (181
  `CONDITION` nodes plus 16 conditional `LINK` nodes). Conditional LINK
  predicates use the same strict evaluator as CONDITION nodes.
