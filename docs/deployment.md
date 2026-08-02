# Deployment

Production deployment is a Jenkins pipeline driving a blue/green Docker
Compose rollout on a single host. This document describes what the
Dockerfiles, compose file, and `deploy/` scripts actually do - it is not a
guide to setting up a new Jenkins server, just a description of the existing
pipeline so you can read or modify it safely.

Performance measurements and the before/after collection template live in
[CI/CD performance baseline](ci-cd-baseline.md).

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

1. **`builder`** (`node:24.18.1-alpine`): enables `pnpm@9.15.9` via corepack, installs
   with `pnpm install --frozen-lockfile` (cached), copies source, then runs
   `pnpm build`. Two build ARGs are exported as ENV so Vite inlines them at
   *build* time: `VITE_TLDRAW_LICENSE_KEY` and `VITE_PRODUCTION` (default
   `0`). **This matters**: the tldraw license key must be present at build
   time, not runtime - without it, tldraw silently hides the whole canvas 5
   seconds after mount when served over HTTPS from a non-localhost domain.
2. **`runtime`** (`nginx:1.27-alpine`): copies `frontend/nginx.conf` to
   `/etc/nginx/conf.d/default.conf` and the built `dist/` to nginx's web
   root. `EXPOSE 80`, healthcheck `wget -qO- http://127.0.0.1/`.

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
| `frontend` | built from `frontend/Dockerfile`, tagged `cdss-frontend:${VERSION:-latest}` | Build args `VITE_TLDRAW_LICENSE_KEY`, `VITE_PRODUCTION` (from `${PRODUCTION:-1}`). Private only, with release-specific alias `cdss-frontend-${VERSION}`. `depends_on: backend (service_healthy)`. |
| `backup` | `postgres:16`, `user: "0:0"` | Runs `deploy/backup_db.sh` (bind-mounted read-only) as its entrypoint, default `command: ["daemon"]`. Writes to a host bind-mount (`${BACKUP_HOST_DIR:-./persistent-backups}`), not a Docker volume - see §"Backups" below. |

Each Jenkins build deploys under an isolated Compose **project name**
`cdss-<VERSION>` (`VERSION` = the Jenkins build number), so every version's
containers/network/volume are fully namespaced and can coexist with the
currently-live version during provisioning. A persistent `cdss-router` nginx
container sits outside the release stacks, owns the public host port, and
atomically routes traffic to one release-specific frontend alias.

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
| `APP_PORT` | `3000` | Public host port owned continuously by the stable `cdss-router`. **The actual Jenkins deployment overrides this to `3001`** (see below). |
| `BACKUP_HOST_DIR` | `./persistent-backups` | Resolves through each release's symlink to `/opt/webapps/cdss/persistent-backups`. It is a real host directory outside release source and mode 0700. |
| `BACKUP_TIMEZONE` / `BACKUP_RETENTION` / `BACKUP_FILE_MODE` | `Asia/Ho_Chi_Minh` / `10` / `0600` | Backup daemon config; SQL dumps are owner-readable only. |

## The Jenkins pipeline (`Jenkinsfile`)

Triggered by `githubPush()` (a GitHub webhook). `disableConcurrentBuilds()`
is set - two deployments must never provision/promote on the same host at
once. Jenkins retains at most 50 builds for 30 days and at most 20 artifact
sets for 14 days. The whole run is limited to 90 minutes, every stage has a
smaller workload-specific timeout, and restart-from-stage is disabled because
it could bypass backup, write-lock, or verification prerequisites. The Verify
Files stage also fails early unless the agent is Linux with Docker daemon
access and every required CLI.

Target host is hardcoded (`TARGET_SERVER=192.168.1.199`,
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
   `backups/backup.sql`, `backups/seed.sql`, and all `deploy/*.sh`
   scripts used later in the pipeline. This means **`backups/backup.sql`
   and `backups/seed.sql` must always be committed and up to date**: a
   broken or missing seed file fails deployment before anything is touched.
3. **Quality Gates**: `deploy/run_quality_gates.sh`, entirely on the Jenkins
   agent, before the deploy target is touched at all. Runs `pytest` (the
   full suite, including the database-marked integration tests, against a
   disposable containerized PostgreSQL), `ruff check`, `ruff format --check`,
   `pyright`, and the frontend's Vitest, Oxlint, TypeScript, and Vite build
   tools. It first regenerates the pregnancy FHIR catalogs so contributor
   changes cannot leave the frontend copy missing or stale. Each frontend
   tool is invoked directly and reports a named failing gate instead of
   pnpm's generic `ELIFECYCLE` wrapper. Any failure stops the pipeline here,
   so a broken build can never reach provisioning or promotion.
4. **Deploy Files**: creates `/opt/webapps/cdss/releases/<version>`,
   `/opt/webapps/cdss/shared`, and the persistent backup directory. It
   migrates legacy flat-checkout state once, then runs `rsync -a --delete`
   (no compression; same-LAN target) from the Jenkins workspace to only the
   versioned release directory,
   excluding `.git`, `.venv`, `node_modules`, `frontend/dist`, `.env*`,
   logs/caches, `scratch`, and the deploy scripts' own runtime state files
   (`deploy/.current_version`, `deploy/.deployment_state`,
   `deploy/.build_state`, `deploy/.router_drain_pending`,
   `deploy/.write_lock`) and `persistent-backups`. Symlinks expose the shared
   environment, state markers, and backups at their legacy release-relative
   paths. A single `deploy/state` directory symlink keeps atomic state-file
   renames inside shared storage, so deploy scripts remain release-local
   without duplicating mutable state.
5. **Inject Environment**: streams the `cdss-prod-env` Jenkins credential
   under remote `umask 077`, strips CRLF, sets mode 0600, and validates
   required keys, duplicates, quoting, production mode, placeholder password,
   numeric values, and backup mode. Only a valid `.env.new` atomically
   replaces `shared/.env`. Deployment scripts read individual values through
   the release's `.env` symlink as dotenv
   data through `deploy/lib.sh`; they never source the file as shell code.
6. **Ensure Live Route**: repairs and verifies the public route to the version
   in `deploy/state/.current_version`, recreating a missing dedicated router
   before lengthy build or migration work begins.
7. **Build Images**: `deploy/build_images.sh <version>`.
8. **Backup Current Database**: `deploy/backup_current_db.sh`.
9. **Enable Write Lock**: reloads the stable router with selective HTTP 503
   responses for layout writes, FHIR imports, and dashboard seed writes. Old
   nginx workers must drain before database cloning can begin.
10. **Provision New Stack**: `deploy/provision_stack.sh <version>`. After
    migration and seed, it requires exactly one Alembic head, verifies the
    database revision, authoritative minimum row counts, one START node per
    tree, and resolvable LINK targets. For cloned production data it
    fingerprints layouts immediately before and after seeding and requires an
    exact match.
11. **Promote New Stack**: `deploy/promote_stack.sh <version>`. Promotion
    preserves the active write-lock marker.
12. **Verify Public Endpoint**: checks `https://cdss.click/` and `/health`
    from the Jenkins agent and requires `X-CDSS-Release` to match the build
    number. A host-local success can therefore no longer hide an external 502.
13. **Disable Write Lock**: reloads and verifies the promoted route without
    write blocking. This runs only after public verification succeeds.
14. **Prune Old Stacks**: `deploy/prune_old_stacks.sh`, followed by
    `deploy/prune_release_dirs.sh`. The previous
    application stack remains available until external verification succeeds
    and writes resume on the new release. A release source directory is
    removed only after its Compose containers are gone; the live version is
    always retained.

The write lock deliberately leaves `POST /evaluate` and all reads available.
It blocks only the known mutating endpoints: tree-layout PUT/DELETE, FHIR
import, and dashboard seed. Failed or aborted builds first restore a verified
route, then disable the lock. If no healthy route can be verified, the lock
remains enabled instead of accepting writes into an uncertain database.

On success: logs `cdss running on <host>:<port> (version <version>)`. On
failure before writes resume, cleanup uses the atomic deployment state to
restore the previous release and database, then removes the candidate. This
automatic rollback is allowed only while the write-lock marker exists. After
writes resume, rollback would discard new database writes, so cleanup instead
repairs and verifies the promoted route. Candidate containers, networks,
volumes, and images are removed by Docker labels and IDs. `cleanWs()`
always runs at the end.

Successful promotion writes `deploy/state/.deployment_state`
(physically `shared/.deployment_state`) atomically with the
current and previous versions, their Git commits, the promotion timestamp, and
status. The `deploy/state/.current_version` file is atomically replaced
last and remains the authoritative commit point for existing scripts.

### Target-host directory layout

```text
/opt/webapps/cdss/
|-- releases/
|   |-- <build-number>/       # immutable source for one Jenkins build
|   |   |-- .env -> ../../shared/.env
|   |   |-- persistent-backups -> ../../persistent-backups
|   |   `-- deploy/state -> ../../../shared
|   `-- ...
|-- shared/                   # mode 0700; env and atomic deploy markers
`-- persistent-backups/       # mode 0700; never rsynced or release-pruned
```

All build, provision, promote, recovery, and prune commands run from the
candidate's release directory. This prevents a later rsync from changing the
scripts or Compose file used by an in-progress or retained release.

## The blue/green deploy scripts (`deploy/`)

All of these (except `lib.sh`, which is sourced, and `seed_database.sh`,
which is only invoked by `provision_stack.sh`) are called directly by the
Jenkinsfile stages above, in the order listed. `deploy/lib.sh` is the shared
helper every other script sources: it detects `docker compose` vs. the
legacy `docker-compose` binary and builds a `$COMPOSE` command scoped to a
given project name (`cdss-<version>`), so every script below operates on one
isolated stack at a time.

### `run_quality_gates.sh`

Runs first, on the Jenkins agent, before the target host is touched.
Self-contained aside from Docker: it creates its own isolated Docker network
and a disposable `postgres:16` container (`-p 54321`, matching the port
`cdss.testing.database`'s safety guard requires), then runs everything else
in ephemeral `uv`/`node` containers on that network. Network and
PostgreSQL container names include Jenkins `BUILD_TAG`, so interrupted or
unrelated jobs cannot remove each other's resources. Named Docker volumes
persist the uv cache, synchronized Python environment, and pnpm content store
across workspace cleanup.

The script regenerates pregnancy FHIR catalogs, runs `alembic upgrade head`,
and imports `backups/seed.sql` before parallel work begins. It then runs
the backend branch (`pytest`, `ruff check`, `ruff format --check`,
`pyright`) concurrently with the frontend branch (Vitest, Oxlint,
TypeScript, and Vite production build). Both branches are awaited so a failure
retains diagnostics from the other branch. Tools are invoked directly, so a
failure identifies its actual phase instead of ending with a generic pnpm
`ELIFECYCLE` message. A `trap ... EXIT`
always removes the container/network/`.env.test` and reclaims ownership of
anything the (root-run, for `corepack enable`) frontend container wrote into
`frontend/`, whether the gate passed or failed.

The quality stage publishes backend and frontend JUnit XML to Jenkins. Backend
pytest also writes coverage XML without enforcing a threshold yet, so the first
reports establish a baseline. Detailed gate durations are stored as TSV files.
Before `cleanWs()`, Jenkins archives only `.ci-reports` directories;
these contain test, coverage, timing, Git/build identity, and
`.deployment_state` evidence. Production `.env` files and Jenkins
credential files are outside the artifact patterns.

### `build_images.sh <version>`

Builds only what changed. Hashes the backend's build inputs
(`Dockerfile.backend`, `pyproject.toml`, `uv.lock`, `src/`, `alembic/`,
`data/`, ...) and the frontend's (everything under `frontend/` excluding
`node_modules`/`dist`, plus the two Vite build args) via `sha256sum`,
compares against a persisted state file (`deploy/state/.build_state`). If a
service's hash is unchanged and its previous version's image still exists,
it's retagged (`docker image tag`) instead of rebuilt; otherwise
`$COMPOSE build <service>` runs. When both services changed they always build
concurrently when the host has at least 4 GiB available memory and two CPUs;
otherwise Compose is capped at one worker. Before a required build, the script
fails fast unless Docker storage has 10 GiB free and the host has 2 GiB
available memory (both thresholds are configurable), records a
`CDSS_BUILD_CAPACITY` line, and prints `docker system df`. BuildKit plain
progress makes cache hits and slow layers visible in Jenkins. State is written
atomically (temp file then `mv`). The script does not automatically run a
host-wide builder prune because the Docker daemon may serve other projects.

### `backup_current_db.sh`

Backs up the **currently live** database before the new stack touches
anything, by running `backup_db.sh backup-now` inside the *old* stack's
`backup` service (`$COMPOSE run --rm --no-deps backup backup-now`), using
credentials read directly from the old `db` container's own environment
(`docker inspect`) rather than from the new `.env` - specifically so a
credential rotation in the freshly injected `.env` can't break this final
backup of the outgoing version. If `deploy/state/.current_version` records no
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
starts the new stack's `db`, waits for `pg_isready`, and - if an old
live version is recorded - clones it via a **streamed `pg_dump` piped
directly into the new `db`'s `psql`** (a transactionally consistent clone
taken while the deployment write lock prevents new mutations). Then runs
`alembic upgrade head` via a one-off `backend` container and seeds via
`deploy/seed_database.sh`. Bounded validation requires the expected Alembic
head, authoritative minimum row counts, exactly one START per decision tree,
resolvable LINK targets, and unchanged operator layouts in preserve mode.
Only then are the new `backend` and private `frontend` started. Both must
pass internal health checks before promotion; neither binds the public host
port.

Seed mode depends on whether this is a fresh install or a clone: fresh →
`SEED_MODE=all` (`seed_database.sh` just streams the whole
`backups/seed.sql`); cloned from a live version → `SEED_MODE=preserve-layouts`.

### `seed_database.sh <mode> [seed_file]`

`all` mode: validates the transaction boundary, then `cat`s
`backups/seed.sql` to stdout. `preserve-layouts` mode additionally
requires exactly one ordered marker pair, then `awk`-strips the lines
between the `-- 5. TREE LAYOUTS` and
`-- 6. MEDICINES REFERENCE CATALOG` comment markers in `seed.sql` before
emitting it - so a stack cloned from a live database (which already has
real operator-edited canvas layouts) doesn't have them overwritten by
whatever layout rows happen to be baked into the seed file. Missing,
duplicated, or reordered markers fail closed. `validate_candidate_db.sh`
then verifies the post-seed database with 30-second statement and 5-second
lock timeouts before candidate services can start.

### `promote_stack.sh <version>`

The zero-downtime cutover, with automatic rollback:

1. Finds the healthy private frontend and its release network.
2. Reuses the dedicated persistent `cdss-router`, or creates it when absent.
   The router has no Compose release labels and the script refuses to adopt
   another container that happens to own the public port.
3. Connects the router to the candidate network and verifies the candidate
   through its unique `cdss-frontend-${VERSION}` alias.
4. Writes and validates a new nginx upstream configuration, then runs
   `nginx -s reload`. Nginx starts new workers atomically and lets old workers
   finish existing requests, while the router retains `APP_PORT` throughout.
5. Adds an `X-CDSS-Release` response header and checks `/` and `/health`
   through the public port. Promotion succeeds only when the header identifies
   the candidate release. On failure, the previous nginx configuration is
   restored and reloaded.
6. On success, starts the new backup service, records
   `deploy/state/.current_version`, waits for old nginx workers to drain, and then
   disconnects obsolete release networks. If a long-running request is still
   active after 30 seconds, a server-local drain marker makes pruning retain
   the old release until a later run confirms that the worker has exited.

### `prune_old_stacks.sh`

Runs last. Discovers old versions purely from `docker ps -a` container
naming (`cdss-<N>-...`), so it can't drift from actual host state. For every
non-current version: always removes its `backend`/`frontend`/`backup`
containers and images by immutable container ID. The exact live release and
backend health are checked again after pruning. It stops each old `db`
container but keeps its volume as a rollback candidate, then removes database
resources for all but the 3 most recent old versions (`KEEP_RETENTION=3`,
hardcoded), so up to 3 stopped database snapshots remain available as rollback
targets at any time.

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
