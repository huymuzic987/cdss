# Getting Started

This guide gets a local backend and frontend running. Database backup/restore
and production procedures are covered in [Operations](operations.md) and
[Deployment](deployment.md).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker Engine with Compose
- Node.js 20+ and `pnpm` for the frontend

## Backend setup

Create `.env` from the example, install dependencies, start PostgreSQL, apply
migrations, and load the decision-tree seed data.

```powershell
Copy-Item .env.example .env
uv sync
docker compose up -d postgres
uv run alembic upgrade head
docker compose exec -T postgres psql -U cdss -d cdss -f - < backups/seed.sql
.\dev.ps1
```

On macOS, Linux, WSL, or Git Bash, use `cp .env.example .env` and `./dev.sh`
for the first and last commands.

The API is available at `http://localhost:8000`; its interactive reference is
at `http://localhost:8000/docs` and raw OpenAPI is at `/openapi.json`.

The seed is required. Alembic creates the schema but does not populate the
clinical decision trees or medicine catalog.

## Frontend setup

In a second terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Vite normally serves the application at `http://localhost:5173` and proxies
backend requests to port 8000.

## Run checks

Fast backend tests do not require a database:

```powershell
uv run pytest -m "not database"
```

Before database-backed tests, create the isolated databases and `.env.test`
described in [Test database safety](testing.md).

Frontend checks:

```powershell
pnpm --dir frontend build
pnpm --dir frontend lint
```

## Common setup problems

- **No trees appear:** migrations were applied, but seed data was not loaded.
- **Port already in use:** see [Operations: port conflicts](operations.md#4-port-conflicts).
- **WSL reload does not notice edits:** restart Uvicorn; Windows-mounted paths
  can prevent filesystem events from reaching the reload watcher.
- **Database test safety error:** do not bypass it. Follow
  [Testing](testing.md) and verify `.env.test` targets an isolated database.

## Next steps

- Read [Architecture](architecture.md) before changing backend boundaries.
- Read [Authoring a tree](cdss/authoring-a-tree.md) before changing clinical logic.
- Read [Frontend](frontend.md) before changing the visualizer or dashboard.
