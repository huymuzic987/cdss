# Operations

Seeding, backups, restore, and port conflicts. For migrations themselves see
[docs/database.md](database.md#alembic-migrations); for how this fits into a
first-time local setup see the [README](../README.md) quickstart; for
production deployment see [docs/deployment.md](deployment.md).

There are two independent kinds of "seed data" in this project, and they do
not overlap:

1. **Decision-tree data** (`decision_trees`/`decision_nodes`/`decision_edges`/
   `node_source_references`, plus the `medicines` catalog) - the clinical
   logic itself. This is what `POST /evaluate` reads.
2. **Clinical/dashboard data** (`patients`/`visits`/...) - imported FHIR
   bundles that back the statistics dashboard only. This has no connection
   to `/evaluate` at all. See [docs/database.md](database.md#clinicaldashboard-data).

## 1. Getting decision-tree data into a fresh database

A fresh `uv run alembic upgrade head` gives you empty tables - no trees, no
medicines. You have two ways to populate them, both documented in
`backups/README.md`:

### Workflow A - Alembic + pure-data seed (recommended for local development)

```bash
uv run alembic upgrade head
psql -d cdss -f backups/seed.sql
```

`backups/seed.sql` is a tracked, pure-`INSERT`-only file (no DDL) - it
assumes the schema already exists from Alembic. It seeds all 14 decision
trees and the 65-drug medicine catalog. This is the right workflow when you
just ran migrations on an empty database and want the same data every other
local checkout has.

### Workflow B - full snapshot restore

```bash
uv run python backups/restore.py
```

`backups/restore.py` **wipes the target database** (`DROP SCHEMA public
CASCADE; CREATE SCHEMA public;`) and replays a full self-contained SQL
snapshot (DDL + data) - you don't need to run Alembic first, the snapshot
recreates the schema itself. Run with no arguments, it picks the most recent
`backups/cdss_prod_*.sql` file committed in this repository (currently
`backups/cdss_prod_20260724.sql`) and restores into the local Docker
database (`postgresql://cdss:cdss@localhost:54321/cdss`, matching
`compose.yaml`). Pass `--dump backups/<file>.sql` to pick a different
snapshot, or `--target <url>` to restore somewhere else.

**Safety:** `restore.py` refuses to run against any non-local host (anything
not in `{localhost, 127.0.0.1, ::1, postgres}`) - it cannot be pointed at a
remote/production database, by design.

### Do not run `dump.py` as part of local setup

`backups/dump.py` reads `DATABASE_URL` from your environment and dumps
**whatever database that points at**: read-only, via a `READ ONLY`
transaction. In a normal engineer's `.env`, `DATABASE_URL` points at your
local Docker Postgres, so running `dump.py` locally just dumps your own
(possibly empty or already-seeded) database back out - it does not pull
anything from production, and running it as a "setup" step accomplishes
nothing. `dump.py` is only useful when you deliberately point `DATABASE_URL`
at a database you want to snapshot (for example, to produce a new
`backups/cdss_prod_<date>.sql` file to commit after real seed data changes),
which is not a normal local-setup task.

**If you find README or onboarding instructions telling you to run
`dump.py` followed by `restore.py` to seed a fresh local setup, that
sequence is stale**: `dump.py` has nothing to read from until you already
have a populated database, so it cannot be the *first* step. Use Workflow A
or Workflow B above instead.

## 2. Seeding the clinical/dashboard data

This is unrelated to decision trees. `POST /dashboard/seed?source=<source>`
(see [complete API reference](api/complete-reference.md#51-post-dashboardseed))
loads one of three FHIR
bundle sources:

- **`preset`**: `data/fhir/preset_patients.json`, 20 synthetic patients,
  committed to this repository.
- **`synthetic`**: `data/fhir/synthetic_patients.json`, 1,000 synthetic
  patients, committed to this repository (~21 MB). Both files are generated
  by `scripts/generate_synthetic_patients.py`, which reads the live
  `medicines` table (so the trees/medicines seed above must already be
  loaded) and writes fully self-contained static JSON - regenerate with:

  ```bash
  uv run python scripts/generate_synthetic_patients.py
  ```

  (Optional `--out-dir` to write elsewhere; default is `data/fhir/`.)

- **`real_test_case`**: imports every `*.json` file in `backups/test_case/`.
  **This directory does not exist in a fresh checkout and is not tracked by
  git.** It is meant to hold the project's real (de-identified) reference
  data as single-snapshot FHIR bundles (no `Encounter` resource - see
  `cdss.infrastructure.db.clinical_import`'s module docstring for the exact
  shape expected). If you need this data, it must be provisioned to you
  separately and placed at `backups/test_case/*.json` by hand; calling this
  endpoint without doing so returns a 404.

The `preset`/`synthetic` bundles are the ones any fresh checkout can
actually seed without extra provisioning.

## 3. Producing a new backup/snapshot

Only relevant if you've changed decision-tree data (or the medicine catalog)
and want to commit a fresh snapshot for other engineers, or if you're
capturing a production backup as part of deployment (see
[docs/deployment.md](deployment.md) for the automated version of this used
in production).

```bash
# DATABASE_URL must point at the database you want to snapshot
uv run python backups/dump.py                      # writes backups/backup.sql
uv run python backups/dump.py backups/cdss_prod_<date>.sql   # explicit path
```

`dump.py` reconstructs DDL from `pg_catalog` (enum types, tables, keys,
indexes) and emits native `COPY` data blocks, read-only. It never writes
credentials into the output. Commit the resulting file under `backups/` if
it's meant to become the new baseline snapshot other checkouts restore from.

## 4. Port conflicts

The local dev Postgres container (`compose.yaml`) publishes on host port
**`54321`**, not the Postgres default `5432`:

```yaml
ports:
  - "54321:5432"
```

This is deliberate - it avoids colliding with a Postgres instance already
installed natively on your machine (Homebrew, a Windows installer, another
project's Docker container) and listening on the standard port `5432`. If
`docker compose up -d postgres` fails to bind, or the app can't connect,
check what's actually listening:

```bash
# macOS/Linux
lsof -iTCP:54321 -sTCP:LISTEN
# Windows PowerShell
Get-NetTCPConnection -LocalPort 54321 -State Listen
```

If something else already owns `54321` specifically (less common, but
possible if you're running more than one project with a similar compose
setup), either stop that process/container or change the host-side port in
your local `compose.yaml` and update `DATABASE_URL` in `.env` to match - but
don't change the container's internal port (`5432`), only the host mapping.

A **native Postgres service listening on `5432`** does not conflict with
this project's default configuration (which never binds host port `5432` at
all) - but if you've manually pointed `DATABASE_URL` at `5432` for any
reason, or you're running a differently-configured compose file, that native
service will win the bind and the container will fail to start or will
silently not be the database your app actually talks to. When in doubt,
confirm which database you're connected to:

```bash
docker compose exec postgres psql -U cdss -d cdss -c 'select current_database(), inet_server_port();'
```

## 5. Test databases

Database-marked tests (`pytest -m database`) never touch your development
database. They use two additional local Docker databases, `cdss_test` and
`cdss_schema_test`, guarded by `src/cdss/testing/database.py`:

```bash
docker compose up -d postgres
docker compose exec postgres createdb -U cdss cdss_test
docker compose exec postgres createdb -U cdss cdss_schema_test
cp .env.test.example .env.test
```

The safety guard (`assert_test_database_configuration`) fails closed unless
**all** of the following hold: `APP_ENV=test`, `ALLOW_DESTRUCTIVE_TEST_DB=true`,
the configured and test URLs resolve to the same host/port/database, the host
is one of the known local Docker hosts, the port is `54321`, the database
name contains `"test"`, and the name is not one of the configured
development/staging/production database names. `.env.test` is loaded
explicitly and does not fall back to `.env` or ambient environment variables,
so a stray `DATABASE_URL` in your shell can never accidentally redirect a
destructive test.

Seeded integration tests (`tests/db/test_seeded_tree_validation.py`,
`tests/db/test_seeded_link_execution.py`,
`tests/db/test_mock_patient_scenarios.py`,
`tests/api/test_seeded_evaluation.py`) require `cdss_test` to already contain
the same decision-tree seed as Workflow A/B above - apply migrations, then
`backups/seed.sql`, against `cdss_test` specifically. A preflight check fails
with clear instructions listing which seeded tree keys are missing if you
skip this. See [docs/testing.md](testing.md) and
[docs/cdss/mock-patient-test-matrix.md](cdss/mock-patient-test-matrix.md) for
what those tests actually assert.

`tests/db/test_schema_migration.py` is destructive (it cycles
`cdss_schema_test` from Alembic base to head) and runs only against that
dedicated database - it cannot touch `cdss_test`'s seeded data.
