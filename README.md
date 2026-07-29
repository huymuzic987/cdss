# Hypertension Clinical Decision Support System

A stateless clinical decision-support API backed by database-defined decision
trees, with a React visualizer and clinical statistics dashboard.

Clinical rules are stored as nodes, edges, conditions, context patches, and
actions in PostgreSQL. Python supplies a generic traversal engine instead of
hardcoding hypertension thresholds or treatment branches.

## Start here

- [Documentation map](docs/README.md) — choose a guide by task or audience.
- [Getting started](docs/getting-started.md) — run the backend and frontend.
- [Architecture](docs/architecture.md) — understand components and request flow.
- [API](docs/api.md) — choose a focused endpoint guide.
- [Decision-tree engine](docs/cdss/README.md) — understand or author clinical logic.

## System at a glance

~~~text
FHIR Bundle
    |
    v
FastAPI API  --->  FHIR import / dashboard data
    |
    v
Generic traversal engine
    |
    v
PostgreSQL decision trees  --->  actions + traversal result
~~~

The backend is a modular monolith with three boundaries:

- domain: framework-independent traversal and clinical orchestration;
- infrastructure: PostgreSQL models and repository implementations;
- API: HTTP validation, coordination, and response serialization.

See [Backend components](docs/components/backend.md) for responsibilities.

## Quick start

Requirements: Python 3.12+, uv, Docker Compose, and Node.js 20+ with pnpm for
the optional frontend.

~~~powershell
Copy-Item .env.example .env
uv sync
docker compose up -d postgres
uv run alembic upgrade head
docker compose exec -T postgres psql -U cdss -d cdss -f - < backups/seed.sql
.\dev.ps1
~~~

The backend runs at http://localhost:8000. Loading seed data is required
because migrations create the schema but not the clinical trees.

Start the frontend separately:

~~~powershell
cd frontend
pnpm install
pnpm dev
~~~

For Linux commands and troubleshooting, see
[Getting started](docs/getting-started.md).

## Checks

- Fast backend tests: uv run pytest -m 'not database'
- Frontend build: pnpm --dir frontend build
- Frontend lint: pnpm --dir frontend lint

Database-backed tests require isolated test databases. Follow
[Test database safety](docs/testing.md) before running them.

## Repository layout

~~~text
src/cdss/     Backend application
frontend/     Visualizer and dashboard
docs/         Task guides and technical references
tests/        Backend tests
backups/      Seed and backup/restore tools
deploy/       Production deployment scripts
~~~

## Important boundaries

- Evaluation is stateless and does not save a patient record.
- Dashboard import persists data, but traversal never reads it.
- Evaluation input is an HL7 FHIR R4 Bundle.
- Cross-tree context paths are versioned interfaces.

Detailed rules live in the
[traversal contract](docs/cdss/traversal-engine-contract.md),
[JSON dialect](docs/cdss/json-dialect.md), and
[context contract](docs/cdss/context-contract.md).

## Operations

- [Operations](docs/operations.md): seeds, backups, restores, and local issues.
- [Deployment](docs/deployment.md): production images and blue/green delivery.
