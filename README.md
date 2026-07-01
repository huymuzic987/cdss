# Hypertension CDSS Backend

A stateless clinical decision-support API built with FastAPI, SQLAlchemy, and
PostgreSQL. Clinical control flow is stored as decision-tree nodes and edges;
the generic traversal engine evaluates the stored JSON dialect without
hardcoded tree or node branching.

The application includes ORM models, Alembic schema management, bulk tree-graph
loading, graph validation, cross-tree traversal, evidence aggregation, and the
`POST /evaluate` endpoint. Evaluation reads definitions and does not persist
patient data or runtime results.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 0.5+
- Docker with Compose
- PostgreSQL 16 through the repository's `postgres` Compose service

## Development

Install dependencies and configure the normal development environment:

```bash
uv sync
cp .env.example .env
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn cdss.main:app --reload
```

The API exposes `GET /health` and `POST /evaluate`. `DATABASE_URL` is required;
normal application configuration continues to load from `.env`.

## Tests

Database tests never use `.env`. They explicitly load the ignored `.env.test`
file and accept only dedicated databases on the local Docker PostgreSQL target.

```bash
cp .env.test.example .env.test
docker compose up -d postgres
uv run pytest -m "not database"
uv run pytest -m database
```

The schema-migration suite is destructive and uses `cdss_schema_test`; seeded
read-only tests use `cdss_test`. See [docs/testing.md](docs/testing.md) before
running database tests.

Quality commands:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

## Architecture

- `src/cdss/domain/decision_tree`: runtime contracts, typed errors, evaluator,
  patch executor, immutable graph model, validator, and walker.
- `src/cdss/infrastructure/db`: SQLAlchemy models and four-query graph loader.
- `src/cdss/api`: FastAPI routes, schemas, dependencies, and safe error mapping.
- `docs/cdss`: frozen traversal contract, seeded JSON dialect, and mock-patient
  matrix.

The schema contains decision definitions, source references, and a development
runtime-log table. It contains no patient table, and normal evaluation does not
write the runtime-log table.

## Alembic

Normal Alembic commands use application settings unless a caller supplies an
explicit Alembic URL:

```bash
uv run alembic current
uv run alembic upgrade head
```

The migration test supplies its guarded `cdss_schema_test` URL directly. Do not
run manual downgrade commands against a populated database.

## Backups

Database snapshots and the dump/restore scripts live in `backups/` (see
[backups/README.md](backups/README.md)). To refresh local from prod anytime:

```bash
uv run python backups/dump.py && uv run python backups/restore.py
```
