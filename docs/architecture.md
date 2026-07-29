# Architecture

This document explains how the CDSS backend is put together: the three-layer
design, why the project is one deployable service instead of several, and what
happens end to end when a client calls `POST /evaluate`.

It describes `src/cdss` as of this writing. For the exact rules the traversal
engine follows, see [docs/cdss/traversal-engine-contract.md](cdss/traversal-engine-contract.md).
For the JSON shapes stored in the database, see [docs/cdss/json-dialect.md](cdss/json-dialect.md).

## The core idea: clinical logic lives in the database, not in Python

The single most important design decision in this codebase is this: **no
clinical rule is written in Python.** There is no `if sbp >= 140` anywhere in
`src/cdss`. Instead, every decision tree (hypertension diagnosis, risk
classification, treatment strategy, drug combination, and so on) is stored as
rows in PostgreSQL: nodes, edges, and JSON condition/patch/action documents on
those nodes.

Python owns exactly one thing: a generic graph-walking engine
(`cdss.domain.decision_tree.walker.walk_tree`) that knows how to evaluate a
JSON condition, apply a JSON context patch, follow an edge, and collect an
action payload. It does not know what `context.risk.level == "HIGH"` means
clinically, or that Tree 3 is called `treatment-threshold-and-bp-target`. It
only knows the shape of the JSON dialect (documented in
[docs/cdss/json-dialect.md](cdss/json-dialect.md)).

The practical consequence: adding or changing clinical logic means editing
rows in `decision_trees`/`decision_nodes`/`decision_edges` (directly, via a
seed script, or via the tree editor described in
[docs/cdss/authoring-a-tree.md](cdss/authoring-a-tree.md)), not shipping a
code change. The engine, the API, and the tests around them are the same
regardless of which of the 14 seeded trees is being walked.

## Why a modular monolith

`src/cdss` is one Python package, one FastAPI process, one deployable
artifact - a modular monolith rather than separate services. The internal
modularity that would normally justify splitting into services is expressed as
package boundaries instead:

- `cdss.domain.decision_tree` has **no** SQLAlchemy or FastAPI imports. It
  operates purely on plain dataclasses/Pydantic models
  (`TreeGraph`, `RunState`, `TraversalResult`) and a `TreeGraphRepository`
  `Protocol` it depends on but does not implement.
- `cdss.infrastructure.db` implements that protocol against PostgreSQL. It is
  the only package that imports SQLAlchemy.
- `cdss.api` wires the two together behind FastAPI routes and Pydantic
  request/response schemas.

Because the domain layer only depends on protocols, it can be (and is) tested
with in-memory fakes and no database at all - see `tests/domain/`. A
service split was never necessary because the whole system serves one
purpose (evaluate decision trees for one clinical workflow) and one dataset;
splitting it would add network calls and deployment complexity without
separating anything that actually changes independently. The three-layer
split gives most of the benefit (testability, replaceable persistence,
clear ownership of clinical-shape decisions) without that cost.

## The three layers

```text
src/cdss/
|-- domain/decision_tree/       # Pure graph, validation, and traversal behavior
|-- domain/follow_up.py         # Hypertension-specific evaluation orchestration
|-- infrastructure/db/          # SQLAlchemy repositories, dashboard queries, FHIR import
\-- api/                        # FastAPI routes, schemas, dependency wiring, error mapping
```

### 1. Domain layer - `cdss.domain.decision_tree`

The domain package has no FastAPI or SQLAlchemy imports. The refactor preserves
the original public modules while extracting cohesive implementation concerns:

| Public module | Focused implementation modules |
| --- | --- |
| `graph.py` | `graph_builder.py`, `graph_freezing.py` |
| `conditions.py` | `condition_evaluator.py`, `condition_operations.py`, `condition_types.py`, `condition_validation.py` |
| `patches.py` | `patch_errors.py`, `patch_operations.py`, `patch_paths.py` |
| `validator.py` | `validation_edges.py`, `validation_errors.py`, `validation_semantics.py`, `validation_topology.py`, `validation_types.py` |
| `walker.py` | `walker_links.py`, `walker_trace.py`, `walker_transitions.py` |

`TreeGraph.build()` still produces immutable indexed graphs, but delegates
construction and recursive JSON freezing. `walk_tree()` remains the execution
entry point and owns the node-entry loop; its internal traversal object composes
link, trace, and transition mixins. Callers should import the public modules,
not the implementation modules.

`actions.py`, `drug_classes.py`, and `medicine_catalog.py` continue to collect
and enrich action payloads. `paths.py` remains the runtime input/context path
resolver. `follow_up.py` sits outside the generic engine because replaying a
previous hypertension visit is application-specific orchestration.

### 2. Infrastructure layer - `cdss.infrastructure.db`

The infrastructure package implements the domain repository protocols and owns
database-backed features outside traversal:

- `decision_tree_repository.py` loads a tree in four bounded queries and hands
  plain rows to `TreeGraph.build()`.
- `caching_repository.py` and `caching_medicine_repository.py` provide opt-in
  caches. `tree_layout_repository.py` stays separate because layouts are
  mutable and must not share the immutable graph cache.
- `dashboard_repository.py` is the stable injected repository. It composes
  focused query mixins from `dashboard_filters.py`, `dashboard_overview.py`,
  `dashboard_outcomes.py`, and `dashboard_patients.py`; shared aggregate types
  live in `dashboard_metrics.py`.
- `clinical_import.import_bundle()` remains the transaction coordinator.
  Parsing, patient/condition upserts, and observation/medication/visit writes
  are delegated to `fhir_import_parsing.py`, `fhir_patient_import.py`, and
  `fhir_resource_writer.py`.

### 3. API layer - `cdss.api`

`cdss.main.create_app()` mounts the same six public routers: `health`,
`evaluation`, `tree_graph`, `tree_layout`, `fhir`, and `dashboard`.
`api/dependencies.py` remains the repository composition point, and
`api/errors.py` maps typed domain errors centrally.

Route URLs and response contracts did not change in the refactor:

- `routes/dashboard.py` is now a composition router over seed, summary, and
  patient routers. Summary construction is further separated into status,
  metrics, usage, and summary modules.
- `routes/fhir.py` owns the endpoint functions; `routes/fhir_export.py` owns
  persisted clinical-record serialization.

## Source-module size boundary

`tests/architecture/test_source_module_size.py` enforces the refactor's module
boundary: production Python behavior modules under `src/cdss` may contain at
most 200 non-empty, non-comment code lines. API schema modules, test helpers,
and the declarative ORM model file are excluded because their size is mostly
data shape rather than behavior. When a behavior module reaches the limit,
extract a cohesive responsibility behind the existing public entry point
instead of moving callers to implementation modules.

Every domain error (`TreeNotFound`, `MissingRuntimePath`,
`NoMatchingTransition`, ...) is a typed Python exception with a `code`,
`details`, and optionally a `partial_run_state`. `api/errors.py` catches
`DecisionTreeError` centrally, writes a human-readable message per error type,
and maps it to an HTTP status (404 for `TreeNotFound`, 422 for clinical/input
errors, 424 for an unresolved cross-tree `LINK`, 500 otherwise). Routes
themselves contain no `try/except` around traversal.

## Request flow: `POST /evaluate`

This is the main clinical endpoint. Full route code:
`src/cdss/api/routes/evaluation.py`.

1. **FastAPI validates the request body** against `EvaluationRequest`:
   `start_tree_key` (non-empty string) and `input`, which - despite the
   name - is not a flat dict of clinical fields. It must be an **HL7 FHIR R4
   `Bundle`** (`resourceType == "Bundle"`).
2. **`bundle_to_input()`** (`api/schemas/fhir_input.py`) walks the bundle's
   `entry` list and converts it into the flat `input.*` object the engine
   actually consumes:
   - `Patient.birthDate` → `age` (computed in years).
   - Blood-pressure `Observation`s (LOINC panel `85354-9`, components `8480-6`
     SBP / `8462-4` DBP) → one of three reading-role key pairs
     (`current_clinic_sbp`/`dbp`, `previous_sbp`/`dbp`, `clinic_1_sbp`/`dbp`),
     selected by a local `reading-role` extension.
   - A small set of lab `Observation`s (ACR, 24h proteinuria) → named numeric
     keys.
   - `Condition` resources coded on a local `clinical-flag` CodeSystem →
     boolean `has_*`/`is_*` flags (true unless `verificationStatus` is
     `refuted`).
   - A `Parameters` resource → everything else (workflow/orchestration state
     like `facility_capability`, `active_bp_target`, or any key the mapper
     doesn't special-case), decoded from `Parameters.parameter`/`part`.
   - Unrecognized resource types are ignored; malformed shapes the mapper
     must act on raise `InvalidFhirInput` (→ HTTP 422).
3. **Optional follow-up inference.** If both `previous_sbp` and `previous_dbp`
   are present in the flattened input, the route:
   - replays that previous reading through `hypertension-diagnosis`
     (`walk_tree` with a synthesized non-follow-up input), then
   - classifies the encounter via `infer_follow_up()`
     (`cdss.domain.follow_up`) into `INITIAL_VISIT`, `LIFESTYLE_FOLLOW_UP`, or
     `MEDICATION_FOLLOW_UP`, recovering the active BP target from the
     replayed run's context when it's a medication follow-up, and
   - injects the inferred flags into today's input; for a follow-up, the
     traversal's actual `start_tree_key` is overridden to
     `treatment-threshold-and-bp-target` regardless of what the caller passed.
4. **`walk_tree(graph, runtime_input, ...)`** runs the traversal (see
   [docs/cdss/traversal-engine-contract.md](cdss/traversal-engine-contract.md)
   for the full node-by-node semantics): the tree named by
   `start_tree_key` (or the follow-up override) is loaded via
   `TreeGraphRepository.get_tree()`, validated, then walked node by node until
   an `END` node or a terminal `ACTION` node (one with no outgoing edges) is
   reached. `LINK` nodes tail-transfer into another tree loaded through the
   same repository, with the same `RunState` carried across.
5. **`EvaluationResponse.from_result()`** serializes the `TraversalResult`.
   By default (`CDSS_DEBUG_OUTPUT=false`) `select_output_actions()` collapses
   a run's action trail down to just its last action - the tree's real
   terminal recommendation - discarding intermediate audit-only actions from
   nodes like drug-combination's duplicate-class check. Set
   `CDSS_DEBUG_OUTPUT=true` to get the full action trail instead, which is
   meant for tree-authoring debugging, not normal clients.
6. Any typed `DecisionTreeError` raised anywhere in steps 3–4 is caught by the
   handler registered in `api/errors.py` and turned into a JSON error body
   with the partial run state attached, instead of propagating as a 500.

`POST /evaluate/follow-up` is a narrower sibling: it skips the replay/
inference step and requires the caller to already know the active BP target,
medication stage, and today's reading; it always starts from
`treatment-threshold-and-bp-target`. See
[complete API reference](api/complete-reference.md) for both endpoints' exact
request/response shapes.

## Statelessness

The traversal engine writes nothing. A `walk_tree()` call reads tree
definitions (and, for combination actions, the medicine catalog) and returns
a result; it creates no patient record, updates nothing, and commits no
SQLAlchemy session. This is a separate concern from the dashboard's clinical
data import (`POST /fhir/import`, `POST /dashboard/seed`), which does persist
patients/visits for statistics purposes - that data has no connection to any
individual `/evaluate` call and is never read by the traversal engine.
