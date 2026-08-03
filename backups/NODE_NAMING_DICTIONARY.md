# Decision-node naming dictionary

This dictionary describes the naming and medication payload conventions used
by `backups/seed.sql`.

## General structure

Use uppercase snake case:

```text
T<TREE_NUMBER>_<NODE_TYPE>_<KEYWORD>_<SUBJECT>[_<QUALIFIER>]
```

| Node type | Example |
|---|---|
| `START` | `T6_START_ENTRY` |
| `CONDITION` | `T6_CONDITION_HAS_PRIOR_PRESCRIPTION` |
| `INFERENCE` | `T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER` |
| `ACTION` | `T6_ACTION_RECORD_RECOMMENDATION` |
| `END` | `T6_END_INITIAL_TWO_DRUG_REGIMEN` |
| `LINK` | `T6_LINK_RESISTANT_HYPERTENSION` |
| `GLOBAL` | `T6_GLOBAL_DRUG_CLASS_GLOSSARY` |

The key node-type segment must match the persisted `node_type`. A node that
derives, selects, starts, adds, combines, or otherwise changes a medication
regimen is an `INFERENCE` and must use `T..._INFERENCE_<KEYWORD>_...`.
Reserve `ACTION` for genuine workflow execution such as recording, admitting,
notifying, or scheduling; the regimen collector never interprets `ACTION`
nodes as medication inferences.

## Inference keywords

The keyword must describe the single operation performed by the node.

| Keyword | Meaning | Regimen effect |
|---|---|---|
| `DETERMINE` | Derive a fact or status | No medication change by default |
| `CLASSIFY` | Assign diagnosis, severity, risk, or population | No medication change by default |
| `SET` | Establish a target, threshold, or context value | No medication change by default |
| `RESTORE` | Restore established context | Restore explicitly listed components |
| `EVALUATE` | Evaluate a clinical measurement or structure | No medication change by default |
| `COMPARE` | Compare current and previous information | No medication change by default |
| `TEST` | Request or interpret a clinical test | No medication change by default |
| `START` | Begin treatment | Establish base regimen alternatives |
| `ADD` | Add treatment | Append separate components |
| `COMBINE` | Establish a simultaneous multidrug regimen | Append all listed components together |
| `SELECT` | Choose between treatments | Preserve separate alternatives |
| `ADJUST` | Modify dose or regimen | Record an adjustment step |
| `CHANGE` | Replace or switch treatment | Record a replacement step |
| `ESCALATE` | Increase treatment intensity | Record an escalation step |
| `REDUCE` | Reduce dose or intensity | Record a reduction step |
| `STOP` | Discontinue treatment | Mark listed components as stopped |
| `KEEP` | Retain selected treatment | Preserve explicitly listed components |
| `MAINTAIN` | Continue the current regimen unchanged | No additions, removals, or adjustments |
| `MONITOR` | Establish medication monitoring | Record monitoring without adding medication |
| `AVOID` | Mark treatment as unsuitable | Record listed components as constraints |

Do not combine two operations in one keyword. For example, use:

```text
T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER_TO_ESCALATED_REGIMEN
```

Do not use:

```text
T6_INFERENCE_ESCALATE_ADD_BETA_BLOCKER
```

## Medication-key structure

Medication inference keys use:

```text
T<TREE>_INFERENCE_<OPERATION>_<DOSE>_<COMPONENTS>[_<QUALIFIER>]
```

- Use `PLUS` for components prescribed together.
- Use `OR` for mutually exclusive alternatives.
- Never use `COMBINE` for an `OR` choice; use `SELECT`.
- Repeat shared components in every alternative: `A_PLUS_C_OR_A_PLUS_D`.
- Include every drug or class delivered by the node.
- Use canonical class codes such as `A`, `B`, `C`, `D`, `MRA`, and `SGLT2I`.
- Add a readable class name when a code may be unclear, such as
  `B_BETA_BLOCKER`.
- Put branch context last: `FOR_HFMREF`, `FOR_HFPEF`, or
  `TO_ESCALATED_REGIMEN`.
- If no dose is specified, the regimen builder applies `LOW_DOSE`.

Only Tree 6 establishes the authoritative `START` regimen on a linked
treatment path. Tree 4 and Tree 5 nodes that present the same initial choices
use `SELECT`, so they remain visible without creating a second base regimen:

```text
T4_INFERENCE_SELECT_A_C_OR_A_D_LOW_TO_USUAL_DOSE
T5_INFERENCE_SELECT_FIXED_DOSE_A_C_OR_A_D_ONE_PILL
T6_INFERENCE_START_LOW_DOSE_A_PLUS_C_OR_A_PLUS_D
```

## Canonical medication groups

Regimen output uses exactly eight top-level groups:

| Group | Meaning |
|---|---|
| `A` | RAS therapy: ACE inhibitor (`ƯCMC`), ARB (`CTTA`), or ARNI |
| `B` | Beta-blocker |
| `C` | Calcium-channel blocker |
| `D` | Diuretic |
| `MRA` | Mineralocorticoid receptor antagonist; also pharmacologically belongs to `D` |
| `SGLT2i` | SGLT2 inhibitor |
| `GLP1RA` | GLP-1 receptor agonist; reserved even when the medicine catalog has no members |
| `Others` | Medicines outside the seven groups above |

Codes and readable aliases identify the same group. For example, `B` and
`Beta-blocker` must collapse to one regimen item. A specific medicine may be
shown as detail under its group, such as `B — Labetalol`; it must not produce
an additional generic `B` item in the same regimen.

When a specific medicine is known, display the medicine before its group:
`Spironolactone (MRA)`, not `MRA (Spironolactone)`. Spironolactone and
Eplerenone are both catalogued as class `D` medicines with subgroup `MRA`;
the regimen display promotes them to the dedicated `MRA` group.

Examples:

```text
T6_INFERENCE_START_LOW_DOSE_A_PLUS_C_OR_A_PLUS_D
T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER
T10_INFERENCE_COMBINE_LOW_DOSE_D_PLUS_SGLT2I_PLUS_MRA_FOR_HFMREF
T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_ADJUSTMENT
```

## English and Vietnamese text

Text must be clinically readable and must agree with the key and payload.
Include canonical class codes where they improve clarity.

```text
Key:
T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER

English:
Add low-dose class B beta-blocker

Vietnamese:
Thêm thuốc chẹn beta nhóm B liều thấp
```

For alternatives, state each complete option:

```text
English:
Start one low-dose regimen: A + C or A + D

Vietnamese:
Khởi trị một phác đồ liều thấp: A + C hoặc A + D
```

Vietnamese text is display content only. The recognizer never scans it for
ABCD class codes.

## Authoritative regimen payload

Every medication inference must store `action_payload.regimen_update`.
The structured payload is authoritative; keys and bilingual text are
human-readable descriptions.

The payload operation must match the key operation:

```json
{
  "regimen_update": {
    "operation": "ADD",
    "components": [
      {
        "selector_kind": "class",
        "code": "B",
        "name": "Beta-blocker",
        "dose_strategy": "LOW_DOSE"
      }
    ]
  }
}
```

Represent alternatives separately so `A+C OR A+D` is never flattened into
`A+C+D`:

```json
{
  "regimen_update": {
    "operation": "START",
    "alternatives": [
      {
        "components": [
          {"selector_kind": "class", "code": "A", "dose_strategy": "LOW_DOSE"},
          {"selector_kind": "class", "code": "C", "dose_strategy": "LOW_DOSE"}
        ]
      },
      {
        "components": [
          {"selector_kind": "class", "code": "A", "dose_strategy": "LOW_DOSE"},
          {"selector_kind": "class", "code": "D", "dose_strategy": "LOW_DOSE"}
        ]
      }
    ]
  }
}
```

`MAINTAIN` is always an explicit no-op:

```json
{
  "regimen_update": {
    "operation": "MAINTAIN",
    "components": []
  }
}
```

The validator rejects mismatched key and payload operations, medication
operations without components or alternatives, and `MAINTAIN` nodes that
contain components.
