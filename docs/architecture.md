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
├── domain/
│   ├── decision_tree/          # Pure clinical traversal engine (no DB or API deps)
│   │   ├── contracts.py        # RunState, TraversalResult, ExecutedAction, TreeMetadata, ...
│   │   ├── graph.py            # Immutable TreeGraph/NodeDefinition/EdgeDefinition + TreeGraphRepository protocol
│   │   ├── walker.py           # walk_tree(): the stateless traversal engine
│   │   ├── conditions.py       # Condition-dialect parsing/evaluation
│   │   ├── patches.py          # Context-patch application (merge + COPY_PATH)
│   │   ├── paths.py            # input./context. path resolver
│   │   ├── validator.py        # Static tree validation (cycles, reachability, edge/condition shape)
│   │   ├── actions.py          # Action-payload collection, incl. medicine-catalog enrichment
│   │   ├── drug_classes.py     # Resolves A/B/C/D drug-class combinations into medicines
│   │   ├── medicine_catalog.py # Medicine dataclass + MedicineRepository protocol
│   │   └── errors.py           # Typed domain errors
│   └── follow_up.py            # Infers today's workflow (initial/lifestyle/medication follow-up)
│                                # from a replayed previous-visit traversal
├── infrastructure/db/          # SQLAlchemy models and repository implementations
│   ├── models.py                    # ORM tables (see docs/database.md)
│   ├── base.py                      # Declarative Base used by Alembic
│   ├── decision_tree_repository.py  # SqlAlchemyTreeGraphRepository: loads a tree in 4 queries
│   ├── caching_repository.py        # Optional in-memory TreeGraph cache (opt-in, off by default)
│   ├── medicine_repository.py       # SqlAlchemyMedicineRepository
│   ├── caching_medicine_repository.py # Optional in-memory medicine-catalog cache (opt-in)
│   ├── tree_layout_repository.py    # Editor canvas layout persistence (separate, mutable, never cached)
│   ├── dashboard_repository.py      # Read access to patients/visits for the statistics dashboard
│   └── clinical_import.py           # FHIR bundle -> patients/visits importer
└── api/
    ├── routes/     # evaluation, tree_graph, tree_layout, fhir, dashboard, health
    ├── schemas/    # Pydantic request/response models, incl. the FHIR Bundle <-> flat-input mapper
    ├── dependencies.py  # FastAPI DI wiring (session -> repository, with/without caching)
    └── errors.py         # Maps typed domain errors to HTTP status codes and JSON bodies
```

### 1. Domain layer - `cdss.domain.decision_tree`

This is the generic engine. It knows the seven `NodeType` values (`START`,
`CONDITION`, `INFERENCE`, `ACTION`, `END`, `LINK`, `GLOBAL`) and the JSON
dialect for conditions and context patches, and nothing else about
hypertension. Key pieces:

- **`graph.py`**: `TreeGraph.build()` takes flat lists of node/edge/reference
  rows and assembles an immutable, validated in-memory graph (`nodes_by_id`,
  `nodes_by_key`, `outgoing_edges_by_node_id` sorted by `traversal_order`,
  etc). All node JSON fields are frozen into `FrozenJsonObject` so a loaded
  graph can never be mutated by a traversal.
- **`walker.py`**: `walk_tree(graph, runtime_input, ...)` is the entire
  execution engine. It is one Python class (`_InternalTraversal`) driving a
  `while True` loop: enter a node, apply side effects for that node type,
  record a trace entry, pick the next node by evaluating outgoing edges in
  `traversal_order`, repeat. It also handles `LINK` nodes by loading another
  tree from the injected `TreeGraphRepository` and tail-transferring into it
  (no call stack, no automatic return - see the traversal contract).
- **`conditions.py` / `patches.py` / `paths.py`**: the pure functions that
  interpret `condition_definition` and `context_patch` JSON. These have zero
  knowledge of any specific tree.
- **`validator.py`**: runs once per tree per run (and again for any newly
  linked tree) before traversal starts: exactly one `START`, no cycles, every
  executable node reachable, every condition/patch well-formed.
- **`actions.py` / `drug_classes.py` / `medicine_catalog.py`**: when an
  `ACTION`/`END` node has a non-null `action_payload`, `collect_action()`
  copies it into the result and, for a small set of known `action_type`
  values, enriches it with resolved medicines from the `medicines` table
  (via an injected `MedicineRepository`, not a hardcoded lookup).
- **`follow_up.py`** (`cdss.domain.follow_up`, not under `decision_tree/`) -
  not part of the generic engine. It is hypertension-specific orchestration
  used only by the `/evaluate` route: given today's input plus a previous
  visit's readings, it replays the previous visit through
  `hypertension-diagnosis` to classify today's encounter as an initial visit,
  a lifestyle follow-up, or a medication follow-up, and to recover the
  active BP target from that replay.

### 2. Infrastructure layer - `cdss.infrastructure.db`

Implements the domain's repository protocols against PostgreSQL via
SQLAlchemy, and owns everything that is not part of the clinical engine but
still needs the database: the statistics dashboard, FHIR clinical-data
import, and the tree editor's saved canvas layout.

- **`SqlAlchemyTreeGraphRepository.get_tree()`** loads one tree in four bounded
  queries (tree row, its nodes, its internal edges via a self-join, its
  source references) and hands the rows to `TreeGraph.build()`. It never
  touches SQLAlchemy relationship lazy-loading, so the query count is fixed
  regardless of tree size.
- **`CachingTreeGraphRepository`** / **`CachingMedicineRepository`** wrap the
  SQL repositories with an in-memory cache. Both are **opt-in**
  (`CDSS_GRAPH_CACHE_ENABLED` / `CDSS_MEDICINE_CACHE_ENABLED`, default off)
  because a stale cached tree after a re-seed is a clinical correctness risk;
  a deployment that enables caching owns invalidation.
- **`TreeLayoutRepository`** is kept deliberately separate from the tree-graph
  repositories: a layout (node x/y positions, connector style) is mutable and
  written on every canvas edit, so it must never share the graph cache that
  treats tree structure as immutable.
- **`DashboardRepository`** / **`clinical_import.py`** are unrelated to
  traversal - they back the statistics dashboard described in
  [docs/frontend.md](frontend.md) and [docs/database.md](database.md).

### 3. API layer - `cdss.api`

FastAPI routes and Pydantic schemas. `cdss.main.create_app()` builds the
`FastAPI` app, registers CORS (wide open - no patient identifier ever crosses
this API), registers the domain-error-to-HTTP-status mapping
(`api/errors.py`), and mounts six routers: `health`, `evaluation`,
`tree_graph`, `tree_layout`, `fhir`, `dashboard`.

`api/dependencies.py` is the only place that decides whether a request gets a
caching or non-caching repository, based on `Settings`. Routes never
instantiate a repository directly.

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
