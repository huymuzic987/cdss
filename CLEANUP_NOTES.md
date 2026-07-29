# Backend Cleanup Notes

Safe cleanup sweep of `src/cdss` (plus `scripts/` and `tests/`), scoped to dead
code removal and provably behavior-preserving efficiency/redundancy fixes.
No changes to the traversal algorithm (`walker*.py`), condition evaluation
(`condition*.py`, `conditions.py`), patch application (`patch*.py`), path
resolution (`paths.py`), or the caching repositories' invalidation logic.
Nothing was reformatted wholesale and no imports were reordered beyond what
each specific edit required.

Method: an AST-based script cross-referenced every top-level function,
class, and constant name in `src/cdss` against the whole repo (`src`,
`tests`, `scripts`, `alembic`) to find anything defined but never referenced
elsewhere; a second pass scanned for runs of consecutive comment-only lines
(possible commented-out code); a third pass manually read through every
in-scope module (dashboard routes/repository, FHIR import/export,
graph-loading, validation, schemas) looking for redundant repeated
computation and redundant boolean/container patterns. `ruff check` was also
used as a baseline, though its findings were all line-length/whitespace/
import-order (formatting), explicitly out of scope for this pass.

## Changes made

### `src/cdss/main.py`
Removed the unused private constant `_FRONTEND_DEV_ORIGIN` (and its
explanatory comment). It was defined but never referenced anywhere -- the
CORS middleware below it uses `allow_origins=["*"]`, not this constant.
Confirmed via a repo-wide reference search before removing. Pure dead code;
no behavior change (it was inert).

### `src/cdss/api/errors.py`
`request_validation_error_handler` called `error.errors()` twice (once to
build `safe_errors`, once to build `errors_summary`). `RequestValidationError.errors()`
is a pure accessor (`return self._errors`, verified by reading the FastAPI
source in this project's venv) with no side effects, so calling it twice
always returns the same list. Hoisted into one `errors = error.errors()` and
reused it in both places. Also removed the trailing whitespace on the one
blank line inside the block already being edited (not a separate formatting
pass).

Covered by `tests/api/test_fhir_routes.py` and `tests/api/test_evaluation.py`
(422 validation-error paths), both still passing.

### `src/cdss/api/schemas/fhir_input.py`
`_apply_observation` computed `_codings(component.get("code"))` twice per
component (once for the SBP check, once for the DBP check) inside an `any()`
generator expression. `_codings()` re-parses the component's `coding` list
into a `dict[str, set[str]]` each call -- real, if small, repeated work.
Hoisted the single per-component result into a `codes := ...` walrus binding
(the same style already used elsewhere in this codebase, e.g.
`clinical_import.py`'s `candidate_dates` computation) and reused it for both
membership checks. Output is identical since `_codings` is a pure function
of `component.get("code")`.

Covered by `tests/api/test_fhir_input.py`, still passing.

### `src/cdss/api/schemas/clinical_evaluation.py`
`_apply_conditions` called `condition.get("code")` four times per loop
iteration (twice guarding/building `codings`, twice guarding/building
`text`). `condition` is a read-only `Mapping` that nothing in the loop body
mutates, so all four calls return the identical object. Hoisted into one
`code_concept = condition.get("code")` at the top of the loop body and
reused it everywhere `condition.get("code")` previously appeared in that
iteration.

Covered by `tests/api/test_canonical_clinical_evaluation.py` and
`tests/api/test_evaluation_follow_up.py`, still passing.

### `src/cdss/api/routes/dashboard_usage.py`
`_build_efficacy` looped over `patients` twice (once for the
adherence-vs-next-visit-BP-control calculation, once for the
medication-change calculation), independently recomputing
`sorted(p.visits, key=lambda v: v.visit_number)` for the same patient in each
loop. Nothing between the two loops mutates any patient's `.visits`, so the
two sorts were always producing identical lists. Hoisted the sort into one
list comprehension computed once (`visits_sorted_by_patient`, in the same
order as `patients`), and had both loops iterate that precomputed list
instead of re-sorting. The loop bodies themselves (including all `continue`
statements and accumulation logic) are untouched -- only where `visits_sorted`
comes from changed, not what either loop does with it.

**Caveat:** there is no test file covering the dashboard aggregation layer at
all (`find tests -iname "*dashboard*"` returns nothing), so this change is
not exercised by the regression suite one way or the other. It's verified
here by direct proof of equivalence (pure hoist of a side-effect-free,
deterministic computation, order-preserving), not by a passing test. Flagging
for extra reviewer attention given the lack of a safety net; a follow-up unit
test for `_build_efficacy`/`_build_cdss_usage` would close this gap.

## Borderline cases considered and deliberately skipped

- **`fhir_input.py`'s `input_to_bundle`, `for key in [k for k in remaining if
  is_clinical_flag_key(k)]:`** -- looks like an unnecessary list build before
  a `for` loop (could look like it should be a generator). It is not
  redundant: the loop body does `remaining.pop(key)`, mutating the same dict
  the comprehension reads from. Materializing the list first is required to
  avoid a "dictionary changed size during iteration" error; a generator or
  direct `for key in remaining` would break. Left unchanged.

- **`dashboard_patients.py`'s `search_patients` route (`_matches`/`_sort_key`
  closures)**: `last_visit(p)` (an O(visits-per-patient) `max()` scan) gets
  called up to 3 times per patient across `_matches`, `_sort_key`, and the
  final page-building loop. This is a real repeated-computation pattern, but
  memoizing it safely means restructuring both closures to accept or look up
  a precomputed value (e.g. a `dict` keyed by patient identity), which
  touches more of the route's logic than the fix is worth: `patient.visits`
  lists are small (single digits to low tens), so `max()` over them is
  microseconds, and the endpoint's own page size cap (`limit<=100`) already
  bounds the expensive part. Judged not "obviously" inefficient enough to
  justify the larger diff. Left unchanged.

- **Repeated single `.get(...)` chains in FHIR import/parsing** (e.g.
  `fhir_resource_writer.py`'s `(observation.get("valueQuantity") or
  {}).get("value")` / `.get("unit")`, and similar patterns throughout
  `clinical_import.py`, `fhir_patient_import.py`): these repeat a single O(1)
  dict lookup, not an actual recomputation of derived data (unlike the
  `_codings()`/`error.errors()`/`condition.get("code")` cases above, which
  each redo real parsing/dedup work). The performance difference is
  effectively zero, and these files sit directly in the FHIR
  import/persistence data pipeline, where I chose to hold a stricter bar and
  not touch anything without a genuine, measurable inefficiency. Left
  unchanged, project-wide.

- **`scripts/generate_synthetic_patients.py`**: reviewed in full for dead
  code (none found -- every private helper is referenced) and inefficiency.
  This script uses `random`, so its output is non-deterministic by design;
  any reordering of its internal computation risks perturbing the sequence
  of `random`/`random.choice`/`random.randint` calls and therefore the
  distribution of generated data in ways that are hard to "prove" identical
  even with the tests passing (there's no test asserting a fixed seed's
  output). Left entirely unchanged as a precaution.

- **`handleChangeArrowKind` ref consistency / `handleResetLayout`
  DELETE-then-PUT ordering** -- not applicable to this backend sweep (these
  are frontend findings from a prior audit); excluded per this task's
  instructions and not touched here either.

## Verification

Baseline (before any change) and after-change runs, both from the repo root:

```
uv run ruff check .
```
Baseline: 26 errors (all in `backups/`, `scratch/`, or line-length/whitespace/
import-order in in-scope files -- none of them dead-code findings).
After: 25 errors -- the one whitespace (`W293`) finding in `api/errors.py`
disappeared as an incidental side effect of the edit there; every other
finding is byte-for-byte the same list. No new findings introduced.

```
uv run pyright
```
Baseline: `226 errors, 0 warnings, 0 informations`.
After: `226 errors, 0 warnings, 0 informations`, and `diff` of the full
output is empty -- identical error set, unrelated to these files (mostly
`JsonValue` union-narrowing noise in test files).

```
uv run pytest -m "not database" -q
```
Baseline: `303 passed, 58 deselected`.
After: `303 passed, 58 deselected` -- identical.

Also re-ran just the test files that exercise the four functions touched by
a real edit (excluding the untested `dashboard_usage.py`, see caveat above):
```
uv run pytest tests/api/test_fhir_input.py tests/api/test_canonical_clinical_evaluation.py \
  tests/api/test_evaluation_follow_up.py tests/api/test_evaluation.py tests/api/test_fhir_routes.py -q
```
`65 passed, 1 warning` (the warning is a pre-existing, unrelated
`httpx`/Starlette deprecation notice).

Database-marked tests (`pytest -m database`) could not be run: Docker was not
available in this environment (`docker ps` failed to reach the daemon). None
of the five edits touch SQL query construction or ORM model definitions, so
this is a coverage gap in verification, not a known risk, but it's worth a
human re-running `uv run pytest -m database` once Docker/Postgres is up
before merging.

No destructive actions were taken. All changes are unstaged; nothing was
committed or pushed.
