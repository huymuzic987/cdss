# Hypertension CDSS — Backend Foundation

A stateless hypertension clinical decision support system, built as a Python
modular monolith. This repository currently contains only the initial backend
foundation: configuration, database session infrastructure, an Alembic setup,
and a `/health` endpoint. No ORM models, migrations, or clinical logic exist yet.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 0.5+
- Docker (run from WSL) for local PostgreSQL
- PostgreSQL 16 (provided via Docker Compose)

## Setup with uv

Install dependencies (including the dev group) into a local `.venv`:

```bash
uv sync
```

## Environment setup

Copy the example file and adjust as needed:

```bash
cp .env.example .env
```

| Variable                       | Purpose                                              |
| ------------------------------ | ---------------------------------------------------- |
| `APP_ENV`                      | `development`, `test`, or `production`               |
| `DATABASE_URL`                 | psycopg2 connection URL (env only)                   |
| `CDSS_MAX_STEPS`               | Safe traversal bound (no traversal code yet)         |
| `DEV_RUNTIME_LOGGING_ENABLED`  | Defaults to true in development/test, false in prod  |

`DATABASE_URL` is read from the environment only; it is never hardcoded.

## Start PostgreSQL (from WSL)

Docker is run by the developer through WSL:

```bash
docker compose up -d postgres
```

Stop it with `docker compose down` (add `-v` to also drop the data volume).

## Run the API

```bash
uv run uvicorn cdss.main:app --reload
```

Then check the health endpoint:

```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"development"}
```

`/health` does not require database connectivity.

## Run tests

```bash
uv run pytest
```

## Lint and type-check

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

## Alembic

Alembic reads `DATABASE_URL` from application settings (see `alembic/env.py`)
and targets the metadata on `cdss.infrastructure.db.base.Base`; importing
`cdss.infrastructure.db.models` registers every table on that metadata.

The initial migration (revision `5c43058f54be`) creates the full schema.

Check the current revision:

```bash
uv run alembic current
```

Apply the migration up to the latest revision:

```bash
uv run alembic upgrade head
```

Roll back one revision (here, drops all tables and the `node_type` enum):

```bash
uv run alembic downgrade -1
```

Roll back the entire schema:

```bash
uv run alembic downgrade base
```

Future schema changes are generated against a running database with:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

These schema migrations are **safe to run before any clinical decision-tree
data is inserted** — they only create structure (tables, enum, constraints,
indexes) and never touch tree/node/edge content. After this phase the database
is **intentionally empty**: the schema exists, but no decision trees, nodes,
edges, or references have been inserted.

### Database-required tests

The schema-migration integration test is marked `database` and is skipped when
no PostgreSQL is reachable. Run only those tests, or exclude them, with:

```bash
uv run pytest -m database        # run the database integration tests
uv run pytest -m "not database"  # skip them (no database needed)
```

## Database Schema

All tables exist purely to describe and traverse bilingual (English/Vietnamese)
clinical decision trees. **There are no patient data tables** — and no clinical
terminology (SNOMED/ICD/LOINC) or drug tables — anywhere in this system.

- **`decision_trees`** — one row per decision tree, keyed by a stable
  `tree_key` and carrying English/Vietnamese names. No status, version, or
  numbering fields.
- **`decision_nodes`** — the nodes of each tree. Each has a `node_type`
  (`START`, `CONDITION`, `INFERENCE`, `ACTION`, `END`, `LINK`, `GLOBAL`),
  bilingual text, and type-specific JSONB payloads (`condition_definition`,
  `context_patch`, `action_payload`, `global_config`). `LINK` nodes point at
  another tree/node by key only (no foreign keys). Unique per `(tree_id,
  node_key)`.
- **`decision_edges`** — topology only: directed `from_node` → `to_node` links
  with a `traversal_order`. No rule expressions, labels, or clinical text live
  here.
- **`node_source_references`** — guideline provenance attached to a node:
  source title, JSONB `section_path`, optional locators, and printed/PDF page
  numbers as `SMALLINT[]`. Guideline metadata is stored inline; there is no
  separate source-documents table.
- **`development_runtime_logs`** — development/test debugging only, constrained
  to `environment IN ('development', 'test')`. No code writes to it yet.
