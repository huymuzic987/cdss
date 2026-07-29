# CDSS Traversal Engine Contract

Status: frozen design contract for the generic, stateless traversal engine.
Re-audited against `src/cdss/domain/decision_tree/` and
`src/cdss/api/routes/` as of this writing; see §16-17 for what changed since
the original audit (the engine's runtime rules in §1-15 are unchanged - only
the surrounding application grew).

This document defines runtime behavior only. It does not authorize database
schema changes, patient persistence, seed changes, API routes, or
hypertension-specific code.

## 1. Scope and invariants

The engine traverses database-defined decision trees without embedding clinical
rules, tree keys, or node keys in Python.

The following invariants apply:

- The caller must provide a `start_tree_key`.
- The caller's input is deep-copied once into `input_snapshot`.
- `input_snapshot` is immutable for the lifetime of the run.
- Runtime-derived values live only in `context`.
- `context` may be changed only by the context-patch executor.
- Actions, trace entries, and references are append-only execution records.
- All output and structured error data must be JSON serializable.
- A run performs no patient-data writes and requires no patient identifier.
- Database access loads tree definitions and evidence only. Traversal does not
  query one node at a time.
- Every root graph and newly loaded linked graph is validated once per run
  before its nodes can be traversed.
- A linked tree replaces the current control flow. Completion does not return
  automatically to the source tree.

## 2. Runtime input

The engine entry point accepts:

```text
start_tree_key: non-empty string
input: JSON object
```

Execution configuration may additionally supply:

```text
max_steps: positive integer, default 300
links_enabled: boolean, default true for the complete engine
```

`input` may contain arbitrary application data required by the stored tree
definitions. The engine does not validate clinical fields globally. It validates
only values and paths as they are used by a condition or context patch.

At execution start, the engine creates:

```text
input_snapshot = deep_copy(input)
context = {}
actions = []
trace = []
references = []
```

No engine component may retain and mutate the caller's input object.

## 3. Run state

`RunState` is the mutable execution container:

```text
input_snapshot: JSON object
context: JSON object
actions: list[ExecutedAction]
trace: list[TraversalTraceEntry]
references: list[ExecutedReference]
```

Mutation rules:

- `input_snapshot` is never mutated.
- `context` is mutated only through validated context patches.
- `actions`, `trace`, and `references` are appended to, never rewritten to
  conceal an earlier execution event.
- A partial `RunState` is attached to execution errors when traversal has
  already started.

The engine may use an internal immutable execution cursor containing the current
tree key, current node identity, visited node identities, and global step count.
That cursor is engine control state, not clinical context.

## 4. Runtime paths

Runtime paths are dot-separated strings rooted at exactly one of:

```text
input.
context.
```

`input.` resolves against `RunState.input_snapshot`. `context.` resolves against
`RunState.context`.

Missing paths are errors when required by a condition or required patch
operation. They never silently evaluate as `false` or `null`. Roots other than
`input` and `context` are invalid.

## 5. Actions

An action is collected whenever an entered `ACTION` or `END` node has a non-null
`action_payload`.

`ExecutedAction` contains at least:

```text
tree_key
node_key
node_type
text_en
text_vi
payload
```

The payload is deep-copied and preserved as stored. The generic engine does not
interpret clinical action keys or action text.

Actions remain in execution order. Earlier actions are retained when a later
unresolved link or other traversal failure occurs.

## 6. Trace

The trace is an ordered explanation of control flow. Step numbering is stable,
starts at 1, and increases monotonically across linked trees.

The trace must represent both:

- selected node entries; and
- outgoing candidate attempts, including rejected conditions.

`TraversalTraceEntry` contains enough structured data to identify:

```text
step
event
tree_key
node_key
node_type
candidate_node_key when applicable
condition_definition when applicable
condition_result when evaluation completed
evaluation_details when applicable
changed_context_paths
```

The exact event enum may be selected during implementation, but it must
distinguish a node entry from a candidate evaluation. Trace entries must not
contain unserializable ORM objects.

The global traversal step limit (`max_steps`) bounds the number of **node
entries** and applies across all linked trees; it is never reset on a link
transfer. Candidate evaluations are recorded in the trace but do not consume the
budget - the limit measures traversal progress (nodes entered), not branch
fan-out, so it does not shrink as trees grow wider. Termination is guaranteed
independently by cycle detection; the step limit is a secondary safety bound.
Trace step numbering is a separate monotonic sequence that still increases on
every entry, including candidate evaluations.

## 7. References

Source references attached to every executed node are aggregated into the run.
An `ExecutedReference` preserves:

```text
tree_key
node_key
reference_order
source_title
section_path
locator
locator_detail
printed_page_numbers
pdf_page_numbers
reference_note
```

References are ordered by execution order and then `reference_order`. Re-entering
the same node must not duplicate the same database reference in the final
aggregate. Candidate nodes that are evaluated but not entered do not contribute
references.

## 8. Tree metadata

`TreeMetadata` represents each loaded/executed tree without treating `GLOBAL`
nodes as control-flow nodes. It contains the tree identity and bilingual names,
plus the `global_config` values from that tree's `GLOBAL` nodes in deterministic
`display_order`.

GLOBAL configurations are metadata. They are not automatically merged into
runtime context and do not emit actions or references through normal traversal.

## 9. Successful result

`TraversalResult` contains:

```text
status: success
input_snapshot
context
actions
trace
references
tree_metadata
started_at
completed_at
```

The API layer may expose `trace` as `traversal_log`, but the domain meaning and
ordering are unchanged.

Success occurs only when:

- an `END` node completes; or
- an `ACTION` node with no outgoing edge completes.

An unresolved external `LINK` is not a successful or completed clinical result.

## 10. Node-type semantics

### START

- Exactly one `START` is required per tree.
- Entering it has no clinical side effect.
- It selects an outgoing target by branch priority.
- It must have at least one outgoing edge.

### CONDITION

- A `CONDITION` is evaluated while it is an outgoing target candidate.
- Its `condition_definition` must be non-null and valid.
- After a successful candidate evaluation, entering the node records the entry
  and then selects one of its outgoing targets.
- It must have at least one outgoing edge.

### INFERENCE

- On entry, apply its `context_patch` if present.
- Record all changed context paths.
- Then select an outgoing target.
- It must have at least one outgoing edge.

### ACTION

- On entry, collect its `action_payload` if present.
- Apply its `context_patch` if present.
- If outgoing edges exist, select a target and continue.
- If no outgoing edge exists, finish successfully.

A terminal `ACTION` is valid and is not equivalent to an unresolved link.

### END

- Apply its `context_patch` if present.
- Collect its `action_payload` if present.
- Finish successfully.
- It must not have an internal outgoing edge.

### LINK

- A LINK may carry a `condition_definition` when it is one of several outgoing
  branch candidates. Evaluate that predicate before entering the LINK.
- Record the node entry and its references.
- Do not follow an internal outgoing edge.
- Resolve and load `link_target_tree_key`.
- If `link_target_node_key` is null, continue from the target tree's `START`.
- Otherwise continue from the exact target node.
- Preserve the same run state and global safety counters.
- Do not return to the source tree after target-tree completion.

### GLOBAL

- Expose its `global_config` through tree metadata.
- Never enter it through normal traversal.
- It is excluded from reachability requirements for executable nodes.

## 11. Edge selection

`decision_edges` contain topology and priority only. Branch conditions are
stored on target nodes.

At every nonterminal node:

1. Read all outgoing edges in ascending `traversal_order`.
2. Reject any edge whose source or target is not an executable node in the same
   tree.
3. For each target in order:
   - if the target has a non-null `condition_definition`, evaluate it;
   - a `CONDITION` target must have a non-null definition;
   - any other target with a null definition is an unconditional match.
4. Record every attempted conditional candidate and result.
5. Select the first matching target.
6. Enter only the selected target.

`traversal_order` is therefore branch priority, not presentation order.

This permits data-defined conditional LINK targets, as used by seeded Tree 3
to select a treatment strategy by facility capability. The engine applies the
same condition grammar to every conditional candidate and does not branch on
node keys or clinical values in code.

If outgoing edges exist but no candidate matches, raise
`NoMatchingTransition`. Selection must never fall back by swallowing condition
errors.

## 12. LINK semantics

Links are cross-tree tail transfers:

- The source `LINK` remains present in trace and evidence.
- The same input snapshot, context, actions, trace, and references continue.
- `link_target_tree_key` is required.
- A null `link_target_node_key` means the target tree's unique `START`.
- A non-null target node key means that exact node, including its normal entry
  side effects.
- Target `GLOBAL` nodes are not executable link destinations.
- A missing target tree raises `LinkTargetNotFound`.
- A missing requested target node raises `LinkTargetNodeNotFound`.
- Known but unseeded targets remain dependency failures, not successful
  outcomes.
- Cycles are detected by `(tree_key, node_id)` identity across all trees.

There is no call stack and no automatic return edge. If returning behavior is
ever required, it must be represented explicitly in stored tree topology or in
a future, separately versioned contract.

## 13. Error model

Engine failures are typed domain errors, not successful clinical results.
Every error serializes:

```text
code
message
tree_key when known
node_key when known
details
partial_run_state when relevant
```

Required error types:

| Error | Meaning |
| --- | --- |
| `TreeNotFound` | Requested initial tree does not exist. |
| `InvalidTreeStructure` | Loaded topology or node payload placement violates the contract. |
| `InvalidStartNode` | A tree does not have exactly one valid START node. |
| `InvalidConditionDefinition` | Condition JSON has a null, malformed, or unsupported shape. |
| `UnsupportedOperator` | A condition requests an operator outside the frozen dialect. |
| `MissingRuntimePath` | A required `input.` or `context.` path cannot be resolved. |
| `InvalidRuntimeValueType` | Resolved operands do not meet strict type requirements. |
| `ContextPatchError` | A patch or ordered operation is malformed or cannot be executed. |
| `NoMatchingTransition` | No outgoing target matched. |
| `LinkTargetNotFound` | A LINK target tree is not seeded/available. |
| `LinkTargetNodeNotFound` | The target tree exists but the requested node key does not. |
| `TraversalCycleDetected` | A node identity repeats in one execution. |
| `TraversalLimitExceeded` | The global configured step limit is exceeded. |
| `LinkNotEnabled` | Internal-tree-only execution reaches a LINK. |

Configuration defects must not be converted into false conditions. Errors
raised after execution starts include the partial run state so callers can
inspect preceding actions, context, trace, and references.

## 14. Persistence boundary

The traversal engine is stateless with respect to patients:

- It creates no patient record.
- It updates no patient record.
- It stores no runtime result as part of normal evaluation.
- It commits no SQLAlchemy session.
- It does not use `development_runtime_logs` unless a separate, explicitly
  invoked diagnostic adapter is added later.

Logging, if later enabled, is an infrastructure concern and must not alter
clinical execution or turn a failed run into a success.

## 15. Repository audit and module placement

The current repository is a `src/`-layout modular monolith. The existing empty
package `cdss.domain.decision_tree` is the appropriate ownership boundary for
the generic engine.

Recommended future layout:

```text
src/cdss/domain/decision_tree/
  contracts.py
  errors.py
  paths.py
  conditions.py
  patches.py
  graph.py
  validator.py
  walker.py

src/cdss/infrastructure/db/
  decision_tree_repository.py

tests/domain/decision_tree/
tests/infrastructure/db/
```

The domain package should depend on repository protocols and immutable graph
objects, not SQLAlchemy models. The infrastructure repository should translate
ORM rows into those domain objects. FastAPI schemas/routes belong under
`cdss.api` only when API integration is requested.

## 16. Current application and test conventions

- FastAPI is created by `cdss.main.create_app()`.
- Routes are unversioned and synchronous. The engine itself is reached only
  through `POST /evaluate` and `POST /evaluate/follow-up`
  (`src/cdss/api/routes/evaluation.py`). The application has grown well
  beyond the engine since the original version of this contract: `GET /health`,
  `GET /trees` and `GET /trees/{tree_key}/graph` (read-only graph export for
  the frontend visualizer), `GET|PUT|DELETE /trees/{tree_key}/layout`
  (editor-canvas layout persistence, unrelated to traversal), `GET /fhir/...`
  (PlanDefinition/Library knowledge export plus clinical Patient
  import/export), and `GET|POST /dashboard/...` (a statistics dashboard over
  imported clinical data). None of the non-evaluation routes touch
  `walk_tree()`. See `docs/api.md` for the full endpoint list and
  `docs/architecture.md` for how the layers fit together.
- `POST /evaluate`'s `input` field is an HL7 FHIR R4 `Bundle`, not a flat
  object; it is converted to the engine's flat `input.*` namespace by
  `cdss.api.schemas.fhir_input.bundle_to_input()` before `walk_tree()` is
  called. `POST /evaluate` also runs hypertension-specific follow-up
  inference (`cdss.domain.follow_up`) ahead of traversal when the input
  carries a previous visit's readings - see `docs/architecture.md`'s request-flow
  walkthrough. Neither of these is part of the generic engine's contract;
  they are callers of it.
- Evaluation uses API response schemas and typed domain-error mapping.
- SQLAlchemy is synchronous.
- `get_engine()` lazily creates one process-wide engine with
  `pool_pre_ping=True`.
- `get_session_factory()` lazily creates one process-wide `sessionmaker` with
  `autoflush=False`, `autocommit=False`, and `expire_on_commit=False`.
- `get_db()` creates one session per dependency invocation and closes it in a
  `finally` block. It does not commit or explicitly roll back.
- Alembic creates a separate engine with `NullPool`.
- Pytest discovers under `tests/` with `src` added to `pythonpath`.
- Pure configuration, ORM metadata, and FastAPI `TestClient` tests do not
  require PostgreSQL.
- Database tests load `.env.test` explicitly and fail closed instead of falling
  back to `.env`, process environment values, or a remote database.
- Seeded tests marked `database` use the dedicated local Docker `cdss_test`
  database and set their PostgreSQL transaction to read-only.
- Schema-migration tests use a separate local Docker `cdss_schema_test` database,
  validate its configured and connected identity immediately before destructive
  work, and cycle only that database from Alembic base to head.
- The current migration tests are stateful within their module: later tests
  assume the first migration test has upgraded the schema.
- A preflight requires the seeded tree keys (now 13 traversable trees plus
  the intentionally-unseeded `hypertension-older-adults` LINK target - see
  §17) and fails with instructions when the local test database has not been
  seeded. As of this audit, `backups/seed.sql` is a tracked, pure-INSERT seed
  file that reproduces this data - see `docs/operations.md`; it did not exist
  at the time of the original audit below.

## 17. Audited repository mismatches (original audit, 2026-06-29)

The original supplied four-table schema and the repository were not
identical. This section is kept for history; the repository has grown
considerably since (see the update below).

- The repository has a fifth table, `development_runtime_logs`.
- `decision_nodes` additionally enforces
  `UNIQUE (tree_id, node_key)`.
- `node_source_references` additionally enforces
  `UNIQUE (node_id, reference_order)`.
- ORM/migration timestamps are non-null.
- The configured populated database was audited read-only on 2026-06-29; its
  actual JSON shapes were recorded in `json-dialect.md` (then named
  `tree-json-dialect.md`).
- `Settings.cdss_max_steps` and `.env.example` use the contract default of 300.

No schema or seed changes were part of that original audit.

### Update: schema and seed data as of this re-audit

- `src/cdss/infrastructure/db/models.py` now defines **14 tables**, not 5:
  the original `decision_trees`/`decision_nodes`/`decision_edges`/
  `node_source_references`/`development_runtime_logs`, plus `tree_layouts`
  (editor canvas layout, added after this contract was first written),
  `medicines` (static drug reference catalog), `symptoms` (static reference
  catalog, currently unused by the traversal engine or any route), and
  `patients`/`patient_conditions`/`visits`/`visit_observations`/
  `visit_medications`/`fhir_import_batches` (clinical data imported from FHIR
  bundles, backing the statistics dashboard - entirely unrelated to
  traversal). See `docs/database.md` for the full schema.
- `backups/seed.sql` is now a tracked, pure-INSERT seed script reproducing 14
  decision trees and the medicine catalog. This resolves the original
  "no seed script exists" finding.
- The seeded tree set has grown from 5 to 14 tree keys (13 traversable, one -
  `hypertension-older-adults` - intentionally left unseeded as a LINK-failure
  test fixture). See `docs/cdss/json-dialect.md` §1 for the current list and
  row counts.
- The stale README self-contradiction noted in the original audit (claiming
  no ORM models/migrations exist, then describing both later in the same
  file) has been corrected in the current `README.md`.
