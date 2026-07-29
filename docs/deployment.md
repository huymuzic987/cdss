# Deployment

Production deployment is a Jenkins pipeline driving a blue/green Docker
Compose rollout on a single host. This document describes what the
Dockerfiles, compose file, and `deploy/` scripts actually do - it is not a
guide to setting up a new Jenkins server, just a description of the existing
pipeline so you can read or modify it safely.

## Images

### `Dockerfile.backend`

Multi-stage build, context is the **repo root** (not `src/`), built with
`uv`:

1. **`builder` stage** (`python:3.12-slim`): copies the `uv`/`uvx` binaries
   from `ghcr.io/astral-sh/uv:latest`, then installs dependencies only
   (`uv sync --frozen --no-install-project --no-dev`, cache/bind-mounted on
   `uv.lock`/`pyproject.toml` so this layer caches independently of app code
   changes) before copying `src/`, `alembic/`, `alembic.ini`, `data/` and
   running `uv sync --frozen --no-dev` again to install the project itself.
2. **`runtime` stage** (`python:3.12-slim`): installs `curl`, creates a
   non-root `appuser` (uid 1000), copies `/app` from the builder stage
   `--chown=appuser:appuser`, sets `PATH="/app/.venv/bin:$PATH"`, runs as
   `appuser`. `EXPOSE 8000`.
3. **Healthcheck:** `curl -f http://localhost:8000/health` (interval 10s,
   timeout 5s, start-period 10s, retries 5) - this is `GET /health`, see
   [complete API reference](api/complete-reference.md#6-health).
4. **CMD:** `uvicorn cdss.main:app --host 0.0.0.0 --port 8000` (no
   `--reload` - that's dev-only, via `dev.sh`/`dev.ps1`).

### `frontend/Dockerfile`

Also multi-stage:

1. **`builder`** (`node:20-alpine`): enables `pnpm@9` via corepack, installs
   with `pnpm install --frozen-lockfile` (cached), copies source, then runs
   `pnpm build`. Two build ARGs are exported as ENV so Vite inlines them at
   *build* time: `VITE_TLDRAW_LICENSE_KEY` and `VITE_PRODUCTION` (default
   `0`). **This matters**: the tldraw license key must be present at build
   time, not runtime - without it, tldraw silently hides the whole canvas 5
   seconds after mount when served over HTTPS from a non-localhost domain.
2. **`runtime`** (`nginx:1.27-alpine`): copies `frontend/nginx.conf` to
   `/etc/nginx/conf.d/default.conf` and the built `dist/` to nginx's web
   root. `EXPOSE 80`, healthcheck `wget -qO- http://localhost/`.

`frontend/nginx.conf` serves the built SPA and reverse-proxies API paths to
the backend container (`http://backend:8000`): exact-match `/health`,
`/trees`, `/evaluate`, plus prefix matches `/fhir/` and `/dashboard`. Every
other path falls back to `index.html` (SPA client-side routing -
though note the frontend currently has no client-side router; see
[docs/frontend.md](frontend.md)). This mirrors the dev-only Vite proxy
config in `frontend/vite.config.ts`, so the frontend's API client
(`api/client.ts`) can use the same relative paths in both environments.

## `docker-compose.prod.yml` vs. `compose.yaml`

`compose.yaml` (repo root) is **dev-only**: a single `postgres:16` service,
hardcoded credentials (`cdss`/`cdss`/`cdss`), published directly on host port
`54321`, no healthchecks, no backend/frontend services. It exists purely so a
developer can run Postgres locally while running the backend/frontend
un-containerized (`dev.sh`/`pnpm dev`).

`docker-compose.prod.yml` is the real production stack: four services on one
private network (`cdss_net`), one named volume (`cdss_pgdata`):

| Service | Image | Notes |
| --- | --- | --- |
| `db` | `postgres:16` | Credentials/db name from `.env` (`POSTGRES_USER`/`PASSWORD`/`DB`). Healthcheck `pg_isready`. |
| `backend` | built from `Dockerfile.backend`, tagged `cdss-backend:${VERSION:-latest}` | Loads `.env` via `env_file`, then **overrides `DATABASE_URL`** to `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}` regardless of any conflicting value in `.env` - it always points at the internal `db` service. `depends_on: db (service_healthy)`. No ports published; only reachable through the frontend's nginx proxy. |
| `frontend` | built from `frontend/Dockerfile`, tagged `cdss-frontend:${VERSION:-latest}` | Build args `VITE_TLDRAW_LICENSE_KEY`, `VITE_PRODUCTION` (from `${PRODUCTION:-1}`). Published on `${APP_PORT:-3000}:80`. `depends_on: backend (service_healthy)`. |
| `backup` | `postgres:16`, `user: "0:0"` | Runs `deploy/backup_db.sh` (bind-mounted read-only) as its entrypoint, default `command: ["daemon"]`. Writes to a host bind-mount (`${BACKUP_HOST_DIR:-./persistent-backups}`), not a Docker volume - see §"Backups" below. |

Each Jenkins build deploys under an isolated Compose **project name**
`cdss-<VERSION>` (`VERSION` = the Jenkins build number), so every version's
containers/network/volume are fully namespaced and can coexist with the
currently-live version during provisioning - this is what makes the
blue/green flow below possible.

## `.env.prod.example`

Template for the production `.env` (never committed filled in - stored as
the Jenkins secret-file credential `cdss-prod-env`, injected during
deployment; see the pipeline below). `DATABASE_URL` is deliberately **not**
in this file - `docker-compose.prod.yml` builds it internally from the
`POSTGRES_*` variables so the backend always talks to the compose-managed
`db` service.

| Variable | Example/default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `production` | |
| `CDSS_MAX_STEPS` | `300` | Traversal safety limit, same meaning as local dev. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `cdss` / `change-me` / `cdss` | Change the password before first real deploy. |
| `APP_PORT` | `3000` | Public host port for the frontend/nginx container. **The actual Jenkins deployment overrides this to `3001`** (see below) - the example's `3000` is a generic default, not what's live. |
| `BACKUP_HOST_DIR` | `./persistent-backups` | Resolved relative to `/opt/webapps/cdss` on the target host. A real host directory, not a Docker volume - Jenkins' rsync deploy step excludes it from `--delete`, and files in it are readable by other SSH users on that host. |
| `BACKUP_TIMEZONE` / `BACKUP_RETENTION` / `BACKUP_FILE_MODE` | `Asia/Ho_Chi_Minh` / `10` / `0644` | Backup daemon config, see below. |

## The Jenkins pipeline (`Jenkinsfile`)

Triggered by `githubPush()` (a GitHub webhook). `disableConcurrentBuilds()`
is set - two deployments must never provision/promote on the same host at
once. Target host is hardcoded (`TARGET_SERVER=192.168.1.199`,
`TARGET_USER=deployer`, `DEPLOY_PATH=/opt/webapps/cdss`), `VERSION` is the
Jenkins build number, `APP_PORT` is set to `3001` in the pipeline itself
(comment: "3000 is already taken by another project on this host" - note
this differs from `.env.prod.example`'s documented default of `3000`).

Stages, in order:

1. **Checkout**: `checkout scm`.
2. **Verify Files**: fails the build immediately if any of a fixed list of
   required files is missing from the checkout: `pyproject.toml`,
   `uv.lock`, `frontend/package.json`, `frontend/pnpm-lock.yaml`,
   `Dockerfile.backend`, `frontend/Dockerfile`, `docker-compose.prod.yml`,
   `backups/backup.sql`, `backups/seed.sql`, and the four `deploy/*.sh`
   scripts used later in the pipeline. This means **`backups/backup.sql`
   and `backups/seed.sql` must always be committed and up to date**: a
   broken or missing seed file fails deployment before anything is touched.
3. **Deploy Files**: `rsync -a --delete` (no compression; same-LAN target)
   from the Jenkins workspace to `deploy@<host>:/opt/webapps/cdss/`,
   excluding `.git`, `.venv`, `node_modules`, `frontend/dist`, `.env*`,
   logs/caches, `scratch`, and the deploy scripts' own runtime state files
   (`deploy/.current_version`, `deploy/.build_state`) and
   `persistent-backups`.
4. **Inject Environment**: copies the `cdss-prod-env` Jenkins credential
   (a file) to the host as `.env.new`, strips CRLF line endings, moves it to
   `.env`.
5. **Build Images**: `deploy/build_images.sh <version>`.
6. **Backup Current Database**: `deploy/backup_current_db.sh`.
7. **Provision New Stack**: `deploy/provision_stack.sh <version>`.
8. **Promote New Stack**: `deploy/promote_stack.sh <version>`.
9. **Prune Old Stacks**: `deploy/prune_old_stacks.sh`.

On success: logs `cdss running on <host>:<port> (version <version>)`. On
failure: tears down the failed new stack
(`docker compose -p cdss-<version> ... down -v --rmi all`) and notes that
`promote_stack.sh` already auto-restarted the previous version if the
failure happened after the port handover (see below) - the pipeline failing
does not mean production is down. `cleanWs()` always runs at the end.

## The blue/green deploy scripts (`deploy/`)

All of these (except `lib.sh`, which is sourced, and `seed_database.sh`,
which is only invoked by `provision_stack.sh`) are called directly by the
Jenkinsfile stages above, in the order listed. `deploy/lib.sh` is the shared
helper every other script sources: it detects `docker compose` vs. the
legacy `docker-compose` binary and builds a `$COMPOSE` command scoped to a
given project name (`cdss-<version>`), so every script below operates on one
isolated stack at a time.

### `build_images.sh <version>`

Builds only what changed. Hashes the backend's build inputs
(`Dockerfile.backend`, `pyproject.toml`, `uv.lock`, `src/`, `alembic/`,
`data/`, ...) and the frontend's (everything under `frontend/` excluding
`node_modules`/`dist`, plus the two Vite build args) via `sha256sum`,
compares against a persisted state file (`deploy/.build_state`). If a
service's hash is unchanged and its previous version's image still exists,
it's retagged (`docker image tag`) instead of rebuilt; otherwise
`$COMPOSE build <service>` runs. State is written atomically (temp file then
`mv`).

### `backup_current_db.sh`

Backs up the **currently live** database before the new stack touches
anything, by running `backup_db.sh backup-now` inside the *old* stack's
`backup` service (`$COMPOSE run --rm --no-deps backup backup-now`), using
credentials read directly from the old `db` container's own environment
(`docker inspect`) rather than from the new `.env` - specifically so a
credential rotation in the freshly injected `.env` can't break this final
backup of the outgoing version. If `deploy/.current_version` records no
prior version (first-ever deploy), this is a no-op.

### `backup_db.sh [backup-now|daemon]`

Runs `pg_dump --format=plain --create --clean --if-exists --no-owner
--no-privileges` to `/backups/cdss-db-<version>-<timestamp>.sql` (atomic:
temp file then `mv`), then prunes old backups beyond `BACKUP_RETENTION`
(default 10) files. `daemon` mode (the `backup` service's default command)
sleeps until local midnight, backs up, and repeats forever, retrying every
5 minutes on failure. This is also what the `backup` compose service runs
continuously in the live stack.

### `provision_stack.sh <version>`

Creates a fully isolated new stack **without disrupting the live one**:
starts only the new stack's `db`, waits for `pg_isready`, and - if an old
live version is recorded - clones it via a **streamed `pg_dump` piped
directly into the new `db`'s `psql`** (a transactionally consistent clone
taken while production keeps serving traffic). Then runs
`alembic upgrade head` via a one-off `backend` container, seeds via
`deploy/seed_database.sh`, and finally starts the new `backend` (polling its
`/health` endpoint). It deliberately does **not** start the new `frontend` -
only one stack can hold the public port at a time, and that handover is
`promote_stack.sh`'s job.

Seed mode depends on whether this is a fresh install or a clone: fresh →
`SEED_MODE=all` (`seed_database.sh` just streams the whole
`backups/seed.sql`); cloned from a live version → `SEED_MODE=preserve-layouts`.

### `seed_database.sh <mode> [seed_file]`

`all` mode: `cat`s `backups/seed.sql` straight to stdout. `preserve-layouts`
mode: `awk`-strips the lines between the `-- 5. TREE LAYOUTS` and
`-- 6. MEDICINES REFERENCE CATALOG` comment markers in `seed.sql` before
emitting it - so a stack cloned from a live database (which already has
real operator-edited canvas layouts) doesn't have them overwritten by
whatever layout rows happen to be baked into the seed file. **This depends
on those exact comment headers existing in `backups/seed.sql`**: if that
file is regenerated without them, `preserve-layouts` mode silently stops
working as intended.

### `promote_stack.sh <version>`

The actual cutover, with automatic rollback:

1. Stops the old stack (`$COMPOSE stop`, containers kept for rollback - not
   removed).
2. As a second, independent safety check, finds and stops any container
   still physically bound to `APP_PORT` regardless of which compose project
   owns it (in case `deploy/.current_version` and the real host state ever
   disagree).
3. Starts the new stack's `frontend` (image already built, `--no-build`).
4. Health-checks both the public HTTP endpoint and the backend's internal
   `/health` (up to 12×5s each).
5. **On success:** starts the new stack's `backup` service, then writes the
   new version to `deploy/.current_version`.
6. **On any failure:** dumps `backend`/`frontend` logs, stops the broken new
   frontend, and restores service - either restarting whatever container
   was previously bound to the port, or restarting the old compose stack -
   then exits non-zero. This is what makes a failed promotion self-healing:
   the pipeline can fail while production keeps serving the previous
   version.

### `prune_old_stacks.sh`

Runs last. Discovers old versions purely from `docker ps -a` container
naming (`cdss-<N>-...`), so it can't drift from actual host state. For every
non-current version: always removes its `backend`/`frontend`/`backup`
containers and images (keeping only the `db` container/volume as a rollback
candidate). Then fully tears down (`$COMPOSE down -v` - container **and**
volume) all but the 3 most recent old versions
(`KEEP_RETENTION=3`, hardcoded), so up to 3 old database snapshots remain
available as rollback targets at any time.

## Backups in production

Two independent backup mechanisms exist simultaneously:

1. The `backup` compose service, running `backup_db.sh daemon` continuously
   in the **live** stack - a daily scheduled `pg_dump` to
   `${BACKUP_HOST_DIR}` on the host (default `./persistent-backups`, outside
   any Docker volume, excluded from Jenkins' rsync `--delete`).
2. `deploy/backup_current_db.sh`, run once per deployment, capturing the
   live database's exact state immediately before a new version is
   provisioned - a point-in-time safety net independent of the daily
   schedule.

Both ultimately call the same `backup_db.sh` script, just with different
triggers (`daemon` vs. `backup-now`).
