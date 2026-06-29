# Test Database Safety

## Local PostgreSQL

All database tests target the existing `postgres` service in `compose.yaml`:

```text
host: localhost
port: 5432
user: cdss
seeded test database: cdss_test
destructive schema-test database: cdss_schema_test
```

Start PostgreSQL and create the two dedicated databases once:

```bash
docker compose up -d postgres
docker compose exec postgres createdb -U cdss cdss_test
docker compose exec postgres createdb -U cdss cdss_schema_test
```

Create the ignored local test configuration from the tracked template:

```bash
cp .env.test.example .env.test
```

Database tests load `.env.test` explicitly. They do not fall back to `.env` or
ambient process settings. `DATABASE_URL` and `TEST_DATABASE_URL` must normalize
to the same `localhost:5432/cdss_test` identity.

Confirm the connected identities without exposing credentials:

```bash
docker compose exec postgres psql -U cdss -d cdss_test -c 'select current_database();'
docker compose exec postgres psql -U cdss -d cdss_schema_test -c 'select current_database();'
```

After confirming `cdss_test`, load the test environment explicitly and apply
the repository's existing migration:

```bash
set -a
source .env.test
set +a
uv run alembic upgrade head
```

This command targets `DATABASE_URL` from `.env.test`; do not run it until the
identity query above returns `cdss_test`.

## Seeded Database

Apply the existing Alembic migration to `cdss_test`, then load the authoritative
Trees 1-5 data into that local database. This repository has no reproducible
seed SQL, migration, or loader, so the test setup cannot create clinical data.
It checks these keys before any seeded integration or API test runs:

```text
hypertension-diagnosis
risk-classification
treatment-threshold-and-bp-target
essential-treatment-strategy
optimal-treatment-strategy
```

The preflight fails with the missing keys when the local database is not
seeded. It never substitutes a hosted database. Seeded fixtures issue
`SET TRANSACTION READ ONLY`, and API tests also compare decision-definition and
runtime-log row counts before and after each request.

Run read-only seeded tests:

```bash
uv run pytest -m database tests/db/test_seeded_tree_validation.py \
  tests/db/test_seeded_link_execution.py tests/db/test_mock_patient_scenarios.py \
  tests/api/test_seeded_evaluation.py
```

## Destructive Schema Tests

`tests/db/test_schema_migration.py` downgrades `cdss_schema_test` to Alembic
base and upgrades it to head. A centralized guard runs immediately before each
destructive operation and requires all of the following:

- `APP_ENV` is exactly `test`.
- `ALLOW_DESTRUCTIVE_TEST_DB` is exactly `true`.
- Configured and test URLs have the same normalized host, port, and database.
- The URL targets the configured local Docker PostgreSQL endpoint.
- PostgreSQL `current_database()` equals the configured test database name.
- The name is dedicated to tests and differs from configured development,
  staging, and production database names.

Failures include only password-free identity diagnostics. The schema suite uses
a database separate from `cdss_test`, so it cannot erase seeded fixtures.

Run it explicitly:

```bash
uv run pytest -m database tests/db/test_schema_migration.py
```

After both local databases are prepared, run the complete suite safely:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

## Intentional External Dependencies

These link targets remain intentionally unseeded and produce typed unresolved
dependency failures with partial execution state:

```text
hypertensive-emergency
hypertension-heart-failure
hypertension-older-adults
hypertension-coronary-artery-disease
hypertension-type-2-diabetes
hypertension-chronic-kidney-disease
drug-combination
resistant-hypertension
```
