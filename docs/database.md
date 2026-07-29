# Database

PostgreSQL, accessed through synchronous SQLAlchemy 2.0 ORM models
(`src/cdss/infrastructure/db/models.py`) and versioned by Alembic
(`alembic/versions/`). This document describes the schema as it exists today,
the four groups of tables it falls into, and the migration history that
produced it. For how the tables are actually loaded and used at runtime, see
[docs/architecture.md](architecture.md).

## Schema at a glance

14 tables, in four groups that map directly onto the layers described in
[docs/architecture.md](architecture.md):

```text
Decision-tree engine data (read by the traversal engine)
├── decision_trees
├── decision_nodes
├── decision_edges
└── node_source_references

Editor-canvas state (read/written by the visualizer, never by the engine)
└── tree_layouts

Reference catalogs (static, seeded, read by the engine's action-collection
code and by clinical import - not decision-tree data)
├── medicines
└── symptoms

Clinical/dashboard data (imported from FHIR bundles, backs the statistics
dashboard - entirely unrelated to traversal)
├── patients
├── patient_conditions
├── visits
├── visit_observations
├── visit_medications
└── fhir_import_batches

Diagnostics (dev/test only)
└── development_runtime_logs
```

`symptoms` is defined and migrated but not currently read by any route or by
the traversal engine - it is reference data seeded for future use (see
`backups/seed.sql`).

## Decision-tree engine tables

These four are exactly what `SqlAlchemyTreeGraphRepository.get_tree()`
(`src/cdss/infrastructure/db/decision_tree_repository.py`) loads, in four
bounded queries, to build a `TreeGraph`.

### `decision_trees`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID, PK | |
| `tree_key` | text, unique, not null | The stable identifier used everywhere else: `start_tree_key` in `/evaluate`, `link_target_tree_key` on a `LINK` node, the URL segment in `/trees/{tree_key}/graph`. |
| `name_en`, `name_vi` | text, unique, not null | Both are unique - no two trees may share a display name in either language. |
| `created_at`, `updated_at` | timestamptz, not null | |

### `decision_nodes`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID, PK | |
| `tree_id` | UUID, FK → `decision_trees.id`, not null | |
| `node_key` | text, not null | Unique per tree (`UNIQUE(tree_id, node_key)`), not globally. |
| `node_type` | Postgres enum `node_type`, not null | `START`, `CONDITION`, `INFERENCE`, `ACTION`, `END`, `LINK`, `GLOBAL` - see [docs/cdss/traversal-engine-contract.md](cdss/traversal-engine-contract.md) for what each does. |
| `text_en`, `text_vi` | text, not null | |
| `condition_definition` | JSONB, nullable | Boolean expression evaluated while this node is an outgoing candidate. See [docs/cdss/json-dialect.md](cdss/json-dialect.md). |
| `context_patch` | JSONB, nullable | Static merge + `COPY_PATH` operations applied on entry. |
| `action_payload` | JSONB, nullable | Opaque structured output collected on entry to an `ACTION`/`END` node. |
| `global_config` | JSONB, nullable | Opaque tree-level config, only meaningful on `GLOBAL` nodes. |
| `link_target_tree_key`, `link_target_node_key` | text, nullable | Only meaningful on `LINK` nodes; scalar columns, not JSON - see json-dialect.md §10. |
| `display_order` | integer, not null, default 0 | Presentation ordering (e.g. for multiple `GLOBAL` nodes); **not** branch priority - that's `decision_edges.traversal_order`. |
| `created_at`, `updated_at` | timestamptz, not null | |

The Postgres enum type `node_type` is created explicitly in the first
migration (`5c43058f54be`) rather than implicitly by the column definition,
specifically so its lifecycle (create/drop) is controlled once instead of
per-column.

### `decision_edges`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID, PK | |
| `from_node_id`, `to_node_id` | UUID, FK → `decision_nodes.id`, not null | |
| `traversal_order` | integer, not null | Branch priority at `from_node_id`: the engine evaluates outgoing edges in ascending order and enters the first matching target. |

Constraints: `UNIQUE(from_node_id, to_node_id)` (no duplicate edge between the
same pair), `UNIQUE(from_node_id, traversal_order)` (no ambiguous priority at
one node), plus indexes on both `from_node_id` and `to_node_id`. Edges carry
no JSON - condition definitions live on the *target* node, not the edge.

### `node_source_references`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID, PK | |
| `node_id` | UUID, FK → `decision_nodes.id`, not null | |
| `source_title` | text, not null | |
| `section_path` | JSONB, not null | Ordered array of `{"number": ..., "title": ...}` objects - evidence metadata, not part of the condition/patch dialect. |
| `locator`, `locator_detail` | text, nullable | |
| `printed_page_numbers`, `pdf_page_numbers` | smallint[], nullable | |
| `reference_note` | text, nullable | |
| `reference_order` | integer, not null, default 0 | |

`UNIQUE(node_id, reference_order)` plus an index on `node_id`. Across the
current 14-tree seed there are 331 reference rows (see
[docs/cdss/json-dialect.md](cdss/json-dialect.md) for the full node/edge/
reference counts).

## Editor-canvas state

### `tree_layouts`

One row per tree that has ever been laid out in the visualizer
(`UNIQUE(tree_id)`, `ON DELETE CASCADE` if the tree is deleted).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID, PK | |
| `tree_id` | UUID, FK → `decision_trees.id`, unique, not null | |
| `arrow_kind` | text, default `'elbow'`, CHECK IN (`'straight'`, `'elbow'`) | |
| `node_positions` | JSONB, not null, default `{}` | Keyed by `node_key`, `{x, y}` per node. |
| `edge_layouts` | JSONB, not null, default `{}` (added by a later migration) | Saved arrow geometry per edge. |
| `created_at`, `updated_at` | timestamptz, not null | |

`node_positions` is deliberately one JSONB blob rather than a normalized
per-node table: it is always read/written as one whole object by the canvas,
never queried per node, and a node later renamed/removed in `decision_nodes`
just leaves a harmless stale key rather than an orphaned row - the frontend
already tolerates missing/extra keys, merging against a freshly computed
automatic layout (see [docs/frontend.md](frontend.md)).
`TreeLayoutRepository` is a separate repository from the tree-graph
repositories specifically so layout's mutability is never accidentally
covered by the tree-graph cache, which assumes structure is immutable
(see [docs/architecture.md](architecture.md)).

## Reference catalogs

### `medicines`

Static drug reference catalog (not patient data - no encounter, patient, or
prescription rows exist in this table). Seeded from `backups/seed.sql` /
`backups/backup.sql` (per `backups/README.md`, 65 drugs at last count).

| Column | Type | Notes |
| --- | --- | --- |
| `drug_id` | text, PK | |
| `name` | text, not null | |
| `drug_class` | text, nullable, indexed | The A/B/C/D letter scheme (A = RAS inhibitor [ACEI/ARB/ARNI], B = beta-blocker, C = calcium-channel blocker, D = diuretic) used by combination-therapy trees - see [docs/cdss/json-dialect.md](cdss/json-dialect.md) §8.1 and [context-contract.md](cdss/context-contract.md) §8. |
| `subgroup`, `route`, `dose_low`, `dose_usual`, `dose_max`, `source`, `link` | text, nullable | |
| `available` | boolean, not null, default true | Combination-therapy resolution (`drug_classes.py`) filters to oral + available drugs; single-drug references (e.g. aspirin prophylaxis) ignore this flag and always return the drug with its `available` value intact. |
| `atc_code` | text, nullable | Added by a later migration for a planned ATC-classification integration; nullable until backfilled. |

### `symptoms`

Static reference catalog (name, ICD-10/SNOMED/LOINC codes, bilingual
descriptions). Seeded from `backups/seed.sql`. Standalone - no foreign keys
to or from any other table, and not currently read by any route or by the
traversal engine.

## Clinical/dashboard data

Everything below is imported from FHIR R4 bundles
(`cdss.infrastructure.db.clinical_import.import_bundle()`, called from
`POST /fhir/import` and `POST /dashboard/seed`) and backs the statistics
dashboard only. **None of it is read by `walk_tree()` or any `/evaluate`
call**: it has no connection to any individual traversal.

### `patients`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID, PK | |
| `fhir_id` | text, unique, not null | The source `Patient.id`; re-imports upsert on this, not duplicate. |
| `gender`, `department` | text, nullable | `department` mirrors the source data's `ai4life` department extension. |
| `birth_date` | date, nullable | |
| `risk_factor_count` | integer, not null, default 0 | |
| `created_at` | timestamptz, not null | |

### `patient_conditions`

One row per `Condition` resource. `icd10_code`/`snomed_code` are plain string
columns, not foreign keys - there is no `diseases` reference table yet;
joining on the code (or adding a backfilled FK) is additive once one exists.
`UNIQUE(patient_id, fhir_condition_id)`.

### `visits`

One row per encounter (initial diagnosis or follow-up), imported from a
FHIR `Encounter` plus its linked `Observation`/`MedicationRequest`
resources. A source bundle with **no** `Encounter` resource at all (a
single-snapshot record, as produced by real-world exports under
`backups/test_case/`) imports as an implicit `visit_number=1` - see
[docs/operations.md](operations.md).

Key columns: `visit_number`, `visit_date`, `facility_capability`,
`is_early_revisit`/`early_revisit_reason`, `scheduled_next_visit_date`,
`clinic_sbp`/`clinic_dbp`, `bp_target_sbp`/`bp_target_dbp`, `bp_controlled`,
`hypertension_class`, `risk_level`, `cdss_recommended_action` (what the CDSS
engine would recommend at this visit - distinct from the medications
actually given, in `visit_medications`), `adherent_to_cdss` (whether the
clinician followed that recommendation - what the dashboard's efficacy
section compares outcomes against). `UNIQUE(patient_id, visit_number)`,
unique `fhir_encounter_id`.

### `visit_observations`

Generic lab/vital readings by LOINC code (`eGFR`, potassium, etc). Blood
pressure is special-cased onto `visits.clinic_sbp`/`clinic_dbp` directly
(almost every dashboard stat needs it); everything else lands here so new
observation types never require a migration.

### `visit_medications`

Actual medications given at a visit. `drug_id` links to `medicines` when the
name matches; `drug_name` is kept denormalized so an unmatched drug (not yet
in the catalog) isn't lost.

### `fhir_import_batches`

Audit record of one import: `source_label`, `patient_count`, `visit_count`,
`error_count`, `errors` (JSONB array), `imported_at`.

## Diagnostics

### `development_runtime_logs`

`request_id`, `environment` (CHECK IN `'development'`, `'test'` - production
is deliberately excluded), `input_payload`/`inference_context`/`journey`/
`output_payload`/`error_payload` (JSONB), `created_at`. Not written by the
traversal engine during a normal `/evaluate` call - see the traversal
contract's persistence-boundary rules
([docs/cdss/traversal-engine-contract.md](cdss/traversal-engine-contract.md)
§14): "It does not use `development_runtime_logs` unless a separate,
explicitly invoked diagnostic adapter is added later." No such adapter is
wired into any current route.

## SQLAlchemy model notes

- All models subclass `Base` (`src/cdss/infrastructure/db/base.py`), a bare
  `DeclarativeBase` whose only job is to register table metadata for Alembic
  autogenerate.
- `get_engine()`/`get_session_factory()`
  (`src/cdss/core/database.py`) are lazy, process-wide singletons -
  importing the module never opens a connection. The engine uses
  `pool_pre_ping=True`; the session factory uses `autoflush=False`,
  `autocommit=False`, `expire_on_commit=False`. `get_db()` (the FastAPI
  dependency) opens one session per request and closes it in a `finally`
  block - it never commits or rolls back on your behalf, so routes that
  write (import, layout save) call `session.commit()` themselves.
- The tree-graph repository never touches SQLAlchemy relationship
  lazy-loading - it loads nodes, edges (via a self-join aliasing
  `decision_nodes` as both source and target), and references in three
  separate `select()` queries plus the tree lookup, so query count is fixed
  regardless of tree size. The dashboard repository, by contrast, does use
  `selectinload()` (eager relationship loading) for `Patient.visits` /
  `Visit.medications` / `Visit.observations` / `Patient.conditions`, because
  most of the dashboard's sections need to iterate full patient graphs in
  Python (cross-visit comparisons don't reduce cleanly to `GROUP BY`) - see
  the module docstring in `dashboard_repository.py` for the reasoning.

## Alembic migrations

The engine URL is **not** stored in `alembic.ini` - `alembic/env.py` falls
back to `Settings().database_url` (i.e. the `DATABASE_URL` environment
variable / `.env` file) if `alembic.ini`/`-x` didn't already supply one.
`alembic.ini` sets `prepend_sys_path = src`, which is why migration scripts
can `import cdss...`. Alembic uses its own engine with `NullPool` (no
connection pooling for one-shot migration runs).

Chronological order (base → head), by `down_revision`:

| Revision | Summary |
| --- | --- |
| `5c43058f54be` (base) | Creates the `node_type` enum and the four core decision-tree tables (`decision_trees`, `decision_nodes`, `decision_edges`, `node_source_references`) plus `development_runtime_logs`. |
| `8cd7e7adc1fb` | Creates `medicines`. |
| `425debaec093` | Creates `fhir_import_batches`, `patients` (with a `comorbidities` JSONB column, later dropped), and `visits` (with an `actual_treatment_action` column, later dropped). |
| `68b4b4838af0` | "Restructure clinical schema for ICD-10/SNOMED/LOINC/ATC alignment." Creates `patient_conditions`, `visit_medications`, `visit_observations`; adds `medicines.atc_code` and `patients.department`; **drops** `patients.comorbidities` and `visits.actual_treatment_action` (any data in those columns is lost on upgrade; downgrade restores the columns but not their prior contents - a lossy round-trip). |
| `4da35a974155` | Creates `tree_layouts`. |
| `b79e1f82c031` | Creates `symptoms`. (Its docstring header says it revises `425debaec093`, but the actual `down_revision` in code is `4da35a974155` - the code is authoritative; the docstring is stale.) |
| `9f7c2d4a1b6e` | Adds `tree_layouts.edge_layouts`. |
| `c7a41e92d830` (head) | **Pure data migration, no schema change.** Raw SQL (`jsonb_set`) rewriting three specific `decision_nodes` rows by `node_key` (`T3_C_LIFESTYLE_RESPONSE_ADEQUATE`, `T3_C_LIFESTYLE_RESPONSE_INADEQUATE`, `T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING`) to raise the lifestyle-response BP-reduction thresholds from 10/5 mmHg to 15/10 mmHg. Downgrade sets them back to 10/5 - a defined, symmetric reverse, but a blind overwrite: any independent edit to those rows between upgrade and downgrade would be lost, not preserved. |

Run migrations with `uv run alembic upgrade head`; see
[docs/operations.md](operations.md) for the full local setup sequence
including when to run this versus when to just restore a snapshot.
