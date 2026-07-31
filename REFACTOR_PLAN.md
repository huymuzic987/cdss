# Refactor Plan: God-File Proposals

Scope: files remaining large or multi-responsibility after the prior split
commits (`f5ca361` on the frontend canvas, `5a9c5fc` across frontend
dashboard/backend). This document proposes splits; it does not perform them,
except where noted "Performed" below, per the task's explicit exception for
a trivially, obviously safe split with zero logic change.

Rough signal used: files over ~300 to 400 lines, or files under that
threshold but visibly mixing unrelated responsibilities. Both codebases were
scanned by raw line count first, then read in full to judge whether the size
reflects genuine mixed responsibilities or just an inherently long, uniform
list (e.g. one schema class per FHIR resource type) that doesn't gain much
from being split.

## Existing project policy: `tests/architecture/test_source_module_size.py`

Worth surfacing before the proposals below: the backend already has an
automated test enforcing a 200-code-line ceiling on `src/cdss` modules
(comments and blank lines don't count toward the limit), and it passes on
`main` today. It carves out exactly three exclusions: everything under
`api/schemas/`, everything under `testing/`, and
`infrastructure/db/models.py` specifically. Every backend file this document
proposes splitting (`clinical_evaluation.py`, `fhir_input.py`, `fhir.py`,
`fhir_clinical.py`, `models.py`) falls inside one of those three carve-outs.
In other words, these aren't files the team failed to notice -- they're the
exact set someone already decided was allowed to grow past the general
limit, presumably because "one class per FHIR resource type" or "one class
per DB table" doesn't shrink meaningfully no matter how you slice the file.
The proposals below stand on their own merits (the split shapes are real and
the import-impact analysis holds), but tightening or removing any of those
three exclusions is a policy decision for the team, not something this pass
assumes needs correcting. No production file outside those three exclusions
exceeds 200 code lines today, so there is no other backend file this test
would flag.

## Why nothing else was performed directly

The task allows performing "a trivially, obviously safe split with zero
logic change." Exactly one candidate met that bar clean enough to act on
without reservation: the frontend's `api/types.ts` (pure type declarations,
erased at runtime, split behind a barrel file so no other file's imports
change, and fully verified by `tsc --noEmit` alone). Every backend candidate
below has at least one of: a shared private helper used by two sections that
would need to move too (a small but real coupling to think through), ORM
relationship/metadata behavior that only a live-database test run can fully
verify (unavailable in this environment), or high import fan-out across the
codebase. None of those failed outright, but none were clean enough to
perform without the kind of review this document exists to enable. All are
proposed only.

---

## Performed

### `frontend/src/api/types.ts` (383 lines before) -> barrel + `api/types/*.ts`

**Why it qualified as trivial:** the file was a flat list of `interface`/
`type` declarations only (no runtime code, no logic), already had clear
section comments (tree graph, tree layout, evaluation, dashboard) marking
natural boundaries, and is erased entirely at compile time, so `tsc --noEmit`
gives a complete, mechanical proof that nothing broke -- there is no runtime
behavior to regress.

**What was done:**
- `api/types/common.ts`: `JsonValue`, `JsonObject`, `NodeType` (shared by the
  other three).
- `api/types/treeGraph.ts`: `TreeSummary`, `TreeGraphNode`, `TreeGraphEdge`,
  `TreeGraphSourceReference`, `TreeGraphGlobalNode`, `TreeGraphResponse`.
- `api/types/treeLayout.ts`: `TreeNodePosition`, `TreeEdgeLayout`,
  `TreeLayoutResponse`, `TreeLayoutRequest`.
- `api/types/evaluation.ts`: `ApiErrorResponse`, `TraceEvent`,
  `TraversalTraceEntry`, `ExecutedAction`, `ExecutedReference`,
  `PartialRunState`, `EvaluationResponse`.
- `api/types/dashboard.ts`: everything from `Count` through
  `PatientSearchParams` (the dashboard/patient-search response shapes).
- `api/types.ts` itself became a 5-line barrel: `export * from './types/common'`
  etc.

**What imports changed:** none, anywhere else in the codebase. Every
existing `import type {...} from '../api/types'` (or `./api/types`)
continues to resolve to the same file and re-export the same names. This was
the entire point of using a barrel instead of updating call sites.

**Verification:** `pnpm exec tsc --noEmit` and `pnpm run lint` both clean
before and after; `pnpm vitest run` unchanged (72 passed, 1 pre-existing
failure unrelated to this file). See the Verification section of
`CLEANUP_NOTES.md` for exact command output.

---

## Proposed

### `src/cdss/api/schemas/clinical_evaluation.py` (547 lines) -- highest priority

**Why it's a god-file, not just long:** it mixes four genuinely different
kinds of content in one module:
1. A large static data table (`KNOWN_BOOLEAN_FLAGS`, a ~65-entry frozenset)
   plus a handful of LOINC/extension-URL constants.
2. The top-level orchestrator (`parse_clinical_bundle`, ~190 lines) that
   walks a Bundle's resources in a specific order and assembles the
   `ParsedClinicalBundle` result.
3. Per-resource-type "apply" functions (`_apply_bp_pair`, `_apply_birth_date`,
   `_apply_extensions`, `_apply_conditions`, `_apply_medications`) that each
   mutate the `runtime`/`details` accumulators for one FHIR resource type.
4. Low-level, resource-agnostic FHIR primitives (`_require_subject`,
   `_first_code`, `_coding_codes`, `_quantity_value`, `_reference_id`,
   `_extension_value`, `_typed_extension_value`, `_parse_date`,
   `_current_bp_evidence`, `_lab_metadata`) that read like a small utility
   library and have no dependency on the orchestration logic above them.

**Proposed split** (new sibling module `clinical_evaluation_support.py`, or a
`clinical_evaluation/` package -- naming is a judgment call for whoever
performs this):

| New module | Contents | Depends on |
|---|---|---|
| `clinical_evaluation_flags.py` | `KNOWN_BOOLEAN_FLAGS`, `LOINC_*`, `CLINICAL_FLAG_SYSTEM`, `READING_ROLE_EXTENSION`, `INPUT_EXTENSION_PREFIX` | nothing (pure data) |
| `clinical_evaluation_primitives.py` | `_require_subject`, `_first_code`, `_coding_codes`, `_quantity_value`, `_reference_id`, `_extension_value`, `_typed_extension_value`, `_parse_date`, `_invalid` | `InvalidFhirInput` only |
| `clinical_evaluation.py` (kept, shrinks to ~250 lines) | `ParsedClinicalBundle`, `parse_clinical_bundle`, the `_apply_*` functions, `_current_bp_evidence`, `_lab_metadata` | imports the two modules above |

**What imports change:** only inside `clinical_evaluation.py` itself (it
gains two `from cdss.api.schemas.clinical_evaluation_flags import ...` /
`..._primitives import ...` lines). Every one of the moved names is private
(`_`-prefixed) and, per the repo-wide reference scan done for Task 1, used
only within this file -- so no other module in the codebase imports any of
them today. `evaluation.py` and `evaluation_follow_up.py` (the two route
modules that call `parse_clinical_bundle`) need no changes at all.

**Why not performed now:** the "apply" functions and the orchestrator share
enough local naming and sequencing (e.g. `details` and `runtime` are threaded
through several of them in a specific order that matters for correctness --
`_apply_extensions` on the *latest* encounter must run after BP resolution,
per the existing comments) that a careless split could silently reorder
something. It's a clean, low-risk split on paper, but this is the file that
decides what clinical flags reach the traversal engine, so it earns a human
review pass rather than being done unattended.

### `src/cdss/api/schemas/fhir_input.py` (434 lines) -- high priority

**Why it's a god-file:** the module's own docstring and internal `# ---`
section comments already describe three distinct, self-contained
directions:
1. `Bundle -> flat input` (`bundle_to_input` and its `_apply_*` helpers,
   `_codings`, `_quantity_value`, `_find_extension`, `_reading_role`).
2. `Parameters <-> JSON value codec` (`_value_to_parameter`,
   `_scalar_parameter_value`, `_parameter_to_value`, `_SCALAR_VALUE_KEYS`) --
   used by *both* directions 1 and 3.
3. `flat input -> Bundle` (`input_to_bundle` and its `_*_resource` builders)
   -- this direction is explicitly documented as existing only for tests and
   worked examples, not for any production code path.

**Proposed split:**

| New module | Contents |
|---|---|
| `fhir_input_codec.py` | `_value_to_parameter`, `_scalar_parameter_value`, `_SCALAR_VALUE_KEYS`, `_parameter_to_value`, `_find_extension`, `_EXT_PARAMETER_IS_ARRAY`, `_ARRAY_ITEM_NAME` |
| `fhir_input_reverse.py` | `input_to_bundle` and every `_*_resource` builder (`_patient_resource`, `_bp_observation_resource`, `_lab_observation_resource`, `_condition_resource`) -- this is the test-only reverse direction |
| `fhir_input.py` (kept, shrinks to ~200 lines) | `bundle_to_input`, `_apply_patient`, `_apply_observation`, `_apply_bp_observation`, `_apply_condition`, `_codings`, `_quantity_value`, `_reading_role`, `is_clinical_flag_key`, the `_BP_READING_ROLES`/`_LAB_OBSERVATIONS`/`_WORKFLOW_FLAG_KEYS` tables |

**What imports change:** `fhir_input.py` would import `_find_extension` and
the codec functions from `fhir_input_codec.py` (used by `_reading_role` in
the forward direction and by both directions of the codec); `fhir_input_reverse.py`
would import `is_clinical_flag_key` and the codec functions back. Outside
this file: `tests/api/test_fhir_input.py` imports `bundle_to_input` and
`input_to_bundle` directly from `cdss.api.schemas.fhir_input` today -- if the
split keeps `input_to_bundle` re-exported from `fhir_input.py` (e.g. `from
.fhir_input_reverse import input_to_bundle` at the bottom of the kept file,
mirroring the barrel approach used for the frontend types split), the test
file needs zero changes; if not, one import line in that test file changes.

**Why not performed now:** `_find_extension` is used by both the forward
mapping (`_reading_role`) and the codec (`_parameter_to_value`). Whichever
module doesn't own it needs to import it from the other, and since
`fhir_input.py` would import codec functions *from* the new codec module,
having the codec module import `_find_extension` *back* from `fhir_input.py`
would create a circular import. The clean fix (move `_find_extension` into
the codec module and have `fhir_input.py` import it back) is straightforward
but is exactly the kind of "one extra decision" that keeps this out of the
"zero-ambiguity" bar for performing it unattended.

### `src/cdss/infrastructure/db/models.py` (500 lines) -- proposed, higher risk

**Why it's a god-file:** it defines every ORM model for four unrelated
schema areas in one file: decision-tree structure (`DecisionTree`,
`DecisionNode`, `DecisionEdge`, `NodeSourceReference`, `TreeLayout`), the
medicine/symptom reference catalog (`Medicine`, `Symptom`), the clinical/
dashboard data (`Patient`, `PatientCondition`, `Visit`, `VisitObservation`,
`VisitMedication`), and import/audit bookkeeping (`FhirImportBatch`,
`DevelopmentRuntimeLog`).

**Proposed split** (all subclassing the existing shared `Base` from
`infrastructure/db/base.py`, unchanged):

| New module | Contents |
|---|---|
| `models_decision_tree.py` | `NodeType` (the SQLAlchemy enum, distinct from the domain `NodeType`), `DecisionTree`, `DecisionNode`, `DecisionEdge`, `NodeSourceReference`, `TreeLayout` |
| `models_medicine.py` | `Medicine`, `Symptom` |
| `models_clinical.py` | `Patient`, `PatientCondition`, `Visit`, `VisitObservation`, `VisitMedication` |
| `models_import.py` | `FhirImportBatch`, `DevelopmentRuntimeLog` |
| `models.py` (kept, becomes a barrel) | `from .models_decision_tree import *` etc., mirroring the frontend `api/types.ts` barrel pattern so every existing `from cdss.infrastructure.db.models import X` elsewhere in the codebase keeps working unchanged |

**What imports change:** none outside `infrastructure/db/`, if the barrel
approach is used (recommended). Every repository/route file currently does
`from cdss.infrastructure.db.models import Patient, Visit, ...` and would
keep working verbatim.

**Why not performed now:** this is the one place where the failure mode
isn't "a broken import tsc/pyright would catch instantly" -- it's ORM
mapper configuration (SQLAlchemy resolves relationships and table metadata
at import time, across whichever files get imported) and Alembic
autogenerate, both of which are only meaningfully exercised by the
database-marked integration tests. Docker/Postgres was not reachable in this
environment (see Verification in `CLEANUP_NOTES.md`), so `pytest -m database`
could not be run to confirm a split like this is airtight. Recommend
performing this split in an environment where those tests can run
immediately before and after, rather than unattended here.

### `src/cdss/api/schemas/fhir.py` (349 lines) -- optional, lower priority

**Why it's borderline:** it sits right at the edge of the size threshold and
mixes two things: a condition-DSL-to-FHIRPath translator
(`condition_to_fhirpath`, `_translate_condition`, `_translate_comparison`,
`_path_to_fhirpath`, `_literal_to_fhirpath`, `_COMPARISON_OPERATOR_SYMBOLS`,
~60 lines) and the PlanDefinition/Library/Bundle FHIR export schemas plus
their `from_graph`/`_build_action` builders (~280 lines). These are two
readable, independent concerns, but the file is not badly over-sized and
each half is already clearly commented off (`# --- Condition DSL ->
FHIRPath translation ---`, `# --- PlanDefinition ---`, `# --- Library
(GLOBAL nodes) ---`, `# --- Bundle ---`).

**Proposed split:** `fhir_condition_translation.py` (the FHIRPath translator
functions) imported by `fhir.py` wherever `condition_to_fhirpath` is called
(just `_build_action`). Low priority: worth doing only if someone is already
touching this file for another reason, not urgent on its own.

### `src/cdss/api/schemas/fhir_clinical.py` (371 lines) -- optional, lowest priority

**Why it's borderline, and why a split isn't obviously worth it:** unlike
the others, this file is long because it enumerates one pydantic model per
FHIR clinical resource type (`Patient`, `Condition`, `Encounter`,
`Observation`, `MedicationRequest`, plus `Bundle`/`ImportResult`), each with
a uniform shape (fields + one `from_row`/`from_visit`/`from_reading`
factory). It is not mixing unrelated responsibilities so much as it is a
long, repetitive, single-purpose list -- the kind of file where splitting
mostly just moves lines around without reducing conceptual complexity.
Could be split one-class-per-file under a `fhir_clinical/` package if the
team's convention favors that, but this is a style preference, not a
correctness or maintainability problem worth prioritizing.

---

## Frontend: nothing else proposed

After the `api/types.ts` split above, no other frontend file exceeds ~300
lines (`canvas/useTreeCanvasScene.ts` at 203 and `dashboard/PatientsPanel.tsx`
at 190 are the next largest, both comfortably below the threshold and each a
single cohesive concern). `panels/DrugToleranceCheckbox.tsx` (185 lines)
looks large for a checkbox modal at a glance, but roughly 15 of those lines
are a JSDoc block documenting a genuinely non-obvious three-way tolerance
decision table, not mixed responsibilities. The prior two split commits
(`f5ca361`, `5a9c5fc`) already did the real work here.
