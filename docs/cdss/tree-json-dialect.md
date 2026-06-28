# Decision-Tree JSON Dialect

Status: frozen runtime dialect with an explicit seed-audit limitation.

## 1. Audit evidence and limitation

The requested audit target is the non-null JSONB stored for the first five
trees:

```text
hypertension-diagnosis
risk-classification
treatment-threshold-and-bp-target
essential-treatment-strategy
optimal-treatment-strategy
```

Those rows cannot be inspected from the current checkout:

- Git contains one commit and no seed SQL, JSON, Python seed loader, data
  migration, or fixture.
- The only migration creates schema and inserts no clinical data.
- The README states that the database is intentionally empty after migration.
- No local `.env` or ambient `DATABASE_URL` is configured.
- No PostgreSQL server was reachable on the repository's documented local
  address during the audit.

Consequently, there are **zero repository-verifiable non-null JSONB values for
Trees 1-5** in this checkout. This document must not pretend that unobserved
action/global keys are actual seed content.

The shapes below freeze the dialect explicitly required by the project brief.
They are the implementation contract for later prompts, but seed-dependent
examples must be rechecked against the real seed artifact as soon as it is
available. Any additional shape found in actual seeds requires a deliberate
contract update; it must not be accepted through permissive ad hoc evaluation.

## 2. JSONB columns

`decision_nodes` contains four nullable JSONB columns:

| Column | Runtime meaning |
| --- | --- |
| `condition_definition` | Boolean expression used while a node is an outgoing candidate. |
| `context_patch` | Static recursive merge and/or ordered context operations on node entry. |
| `action_payload` | Opaque action data copied into the result. |
| `global_config` | Opaque tree-level configuration exposed as metadata from GLOBAL nodes. |

`node_source_references.section_path` is also JSONB, but it is evidence metadata,
not part of the condition/patch dialect. Its actual seeded shape is unavailable
in this checkout.

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
context.risk.level
context.treatment.bp_target
context.treatment.bp_target.sbp.upper_exclusive_mmhg
```

Path segments traverse JSON objects by exact key. Missing paths raise a typed
error when evaluated or required by a patch. There is no fallback value, string
coercion, array-index syntax, wildcard, or implicit root.

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

The values and field names in examples illustrate syntax only because the seed
rows are unavailable.

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

## 6. Operators and strict types

The frozen operator set is:

```text
eq
lt
lte
gt
gte
```

Semantics:

| Operator | Meaning |
| --- | --- |
| `eq` | Strict equality without string/number coercion. |
| `lt` | Numeric left operand is less than numeric right operand. |
| `lte` | Numeric left operand is less than or equal to numeric right operand. |
| `gt` | Numeric left operand is greater than numeric right operand. |
| `gte` | Numeric left operand is greater than or equal to numeric right operand. |

Rules:

- `lt`, `lte`, `gt`, and `gte` require numeric operands.
- JSON booleans are not numeric, even though Python's `bool` subclasses `int`.
- Numeric strings such as `"140"` are not coerced.
- Missing paths raise `MissingRuntimePath`.
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
content.

The current repository provides no seeded action payload from which actual keys
can be documented. The project brief identifies an expected Vietnamese
action/end text:

```text
Tiếp tục theo dõi và duy trì phác đồ
```

It does not establish whether that text is stored in `text_vi`, inside
`action_payload`, or both. That storage detail remains seed-verification work
and must not be invented in engine code.

## 9. Global configuration

`global_config` is a JSON object attached to `GLOBAL` nodes. The generic engine:

- preserves it as stored;
- exposes it through `TreeMetadata`;
- orders multiple GLOBAL nodes deterministically by `display_order`;
- does not enter GLOBAL nodes;
- does not automatically merge it into runtime context; and
- does not interpret clinical keys.

No non-null seeded `global_config` is available in the repository, so its
internal keys and value types cannot be claimed as audited.

## 10. Link fields are not JSON dialect

Cross-tree links use scalar columns:

```text
link_target_tree_key
link_target_node_key
```

They are not encoded in a JSONB payload. The project brief lists these expected
unseeded target keys:

```text
hypertensive-emergency
hypertension-heart-failure
hypertension-older-adults
hypertension-coronary-artery-disease
hypertension-type-2-diabetes
hypertension-chronic-kidney-disease
drug-combination
resistant-hypertension
```

Their absence must produce typed unresolved-link failures, not terminal success.

## 11. Seed verification checklist

When the seed artifact or populated test database becomes available, re-audit
Trees 1-5 before implementing the evaluator:

1. Export every non-null `condition_definition`, `context_patch`,
   `action_payload`, and `global_config` with tree/node identity.
2. Confirm whether all condition objects fit the mutually exclusive grammar
   above.
3. Confirm exact subtraction object placement and operand keys.
4. Confirm whether `required` is always present on `COPY_PATH`.
5. Record actual action payload keys without assigning them engine semantics.
6. Record actual global configuration keys without merging them into context.
7. Inspect `section_path` shapes for evidence serialization.
8. Add any newly observed shape to this document and its tests before accepting
   it in runtime code.

Until that audit is possible, implementation must remain strict to this frozen
dialect rather than use a permissive expression interpreter.
