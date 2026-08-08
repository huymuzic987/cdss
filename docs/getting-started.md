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

Install the backend and frontend dependencies, then start the appropriate
development launcher. It starts the local Compose PostgreSQL database when
needed, waits for the database, applies migrations, refreshes seed data when
needed, and starts the backend and frontend.

```powershell
uv sync
pnpm --dir frontend install
.\dev.ps1
```

On macOS, Linux, WSL, or Git Bash, use `./dev.sh` for the launcher.

No `.env` file is required for the default local Compose database. The
launchers use `DATABASE_URL` from the environment first, then `.env`, and then
the local Compose fallback. Create `.env` from the example only when you need
to override the default database:

```powershell
Copy-Item .env.example .env
```

The API is available at `http://localhost:8000`; its interactive reference is
at `http://localhost:8000/docs` and raw OpenAPI is at `/openapi.json`.

The launcher seeds a new database after migrations. When `backups/seed.sql`
changes, `scripts/ensure_seed.py` refreshes the decision-tree graph while
preserving clinical and dashboard data plus reference catalogs already in the
database.

## Frontend setup (manual alternative)

The development launcher already starts Vite. Use this standalone workflow
only when you intentionally want to run the frontend without the launcher:

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

- **No trees appear:** rerun the launcher and check its seed output.
- **Port already in use:** see [Operations: port conflicts](operations.md#4-port-conflicts).
- **WSL reload does not notice edits:** restart Uvicorn; Windows-mounted paths
  can prevent filesystem events from reaching the reload watcher.
- **Database test safety error:** do not bypass it. Follow
  [Testing](testing.md) and verify `.env.test` targets an isolated database.

## Next steps

- Read [Architecture](architecture.md) before changing backend boundaries.
- Read [Authoring a tree](cdss/authoring-a-tree.md) before changing clinical logic.
- Read [Frontend](frontend.md) before changing the visualizer or dashboard.
