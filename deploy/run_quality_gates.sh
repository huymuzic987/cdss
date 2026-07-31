#!/usr/bin/env bash
# Pre-deployment quality gate, run on the Jenkins agent itself (not the
# deploy target) before any later stage touches production. All of pytest
# (including the database-marked integration tests), ruff, pyright, and the
# frontend's vitest/oxlint/build must pass, or the pipeline stops here and
# promotion never happens.
#
# Runs everything inside ephemeral containers so the only host dependency is
# Docker -- no assumption that uv/Python/Node/pnpm/PostgreSQL are installed
# on the agent directly.
set -euo pipefail

NETWORK="cdss-ci-net"
POSTGRES_CONTAINER="cdss-ci-postgres"

# Hardcoded to 54321: cdss.testing.database's fail-closed safety guard
# rejects any test database target whose port isn't exactly this value (it
# must match compose.yaml's local-dev port, so a test can never silently
# point at a real deployment). The disposable PostgreSQL server is started
# on this port directly, so other containers on $NETWORK can reach it as
# postgres:54321, which also satisfies the guard's allowed-host list.
TEST_DB_PORT=54321
PG_USER=cdss
PG_PASSWORD=cdss
PG_ADMIN_DB=cdss
TEST_DB_NAME=cdss_test
SCHEMA_TEST_DB_NAME=cdss_schema_test

UV_IMAGE="ghcr.io/astral-sh/uv:python3.12-bookworm-slim"
NODE_IMAGE="node:20-alpine"

HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

cleanup() {
    # The frontend container runs as root (corepack enable needs to write
    # shims under /usr/local/bin), so node_modules/dist it writes into the
    # bind-mounted frontend/ directory come back root-owned. Reclaim them
    # unconditionally so Jenkins' cleanWs() can always delete the workspace,
    # even after a failed gate.
    docker run --rm -v "$PWD/frontend":/workspace alpine:3 \
        chown -R "${HOST_UID}:${HOST_GID}" /workspace > /dev/null 2>&1 || true
    docker rm -f "$POSTGRES_CONTAINER" > /dev/null 2>&1 || true
    docker network rm "$NETWORK" > /dev/null 2>&1 || true
    rm -f .env.test
}
trap cleanup EXIT

# Defensive: clear out anything left behind by a previous run that never
# reached its own cleanup (e.g. the agent was killed mid-build).
cleanup

docker network create "$NETWORK" > /dev/null

echo "Starting disposable PostgreSQL for the database-backed test suite..."
docker run -d --name "$POSTGRES_CONTAINER" \
    --network "$NETWORK" --network-alias postgres \
    -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB="$PG_ADMIN_DB" \
    postgres:16 -p "$TEST_DB_PORT" > /dev/null

ready=""
for _ in $(seq 1 30); do
    if docker exec "$POSTGRES_CONTAINER" pg_isready -p "$TEST_DB_PORT" -U "$PG_USER" > /dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
if [ -z "$ready" ]; then
    echo "ERROR: disposable PostgreSQL did not become ready in time" >&2
    exit 1
fi

docker exec "$POSTGRES_CONTAINER" psql -p "$TEST_DB_PORT" -U "$PG_USER" -d "$PG_ADMIN_DB" \
    -c "CREATE DATABASE ${TEST_DB_NAME};" > /dev/null
docker exec "$POSTGRES_CONTAINER" psql -p "$TEST_DB_PORT" -U "$PG_USER" -d "$PG_ADMIN_DB" \
    -c "CREATE DATABASE ${SCHEMA_TEST_DB_NAME};" > /dev/null

TEST_DATABASE_URL="postgresql://${PG_USER}:${PG_PASSWORD}@postgres:${TEST_DB_PORT}/${TEST_DB_NAME}"
SCHEMA_TEST_DATABASE_URL="postgresql://${PG_USER}:${PG_PASSWORD}@postgres:${TEST_DB_PORT}/${SCHEMA_TEST_DB_NAME}"

# tests/conftest.py's fail-closed fixtures load this file explicitly and
# never fall back to real environment variables -- see
# cdss/testing/database.py. cdss_schema_test is deliberately left empty:
# tests/db/test_schema_migration.py drives its own downgrade/upgrade.
cat > .env.test <<EOF
APP_ENV=test
DATABASE_URL=${TEST_DATABASE_URL}
TEST_DATABASE_URL=${TEST_DATABASE_URL}
TEST_DATABASE_NAME=${TEST_DB_NAME}
ALLOW_DESTRUCTIVE_TEST_DB=true
SCHEMA_TEST_DATABASE_URL=${SCHEMA_TEST_DATABASE_URL}
SCHEMA_TEST_DATABASE_NAME=${SCHEMA_TEST_DB_NAME}
DEVELOPMENT_DATABASE_NAME=cdss
STAGING_DATABASE_NAME=
PRODUCTION_DATABASE_NAME=
EOF

echo "Migrating the disposable test database to head..."
docker run --rm --network "$NETWORK" \
    -v "$PWD":/workspace -w /workspace \
    -e DATABASE_URL="$TEST_DATABASE_URL" \
    -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv-cache -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
    --user "${HOST_UID}:${HOST_GID}" \
    "$UV_IMAGE" \
    sh -c "uv sync --frozen && uv run alembic upgrade head"

echo "Seeding the disposable test database (trees, medicines, symptoms reference data)..."
docker exec -i "$POSTGRES_CONTAINER" psql -p "$TEST_DB_PORT" -U "$PG_USER" -d "$TEST_DB_NAME" \
    < backups/seed.sql > /dev/null

echo "Running backend quality gates: pytest, ruff check, ruff format --check, pyright..."
docker run --rm --network "$NETWORK" \
    -v "$PWD":/workspace -w /workspace \
    -e DATABASE_URL="$TEST_DATABASE_URL" \
    -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv-cache -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
    --user "${HOST_UID}:${HOST_GID}" \
    "$UV_IMAGE" \
    sh -c "
        set -e
        uv sync --frozen
        uv run pytest
        uv run ruff check
        uv run ruff format --check
        uv run pyright
    "

echo "Running frontend quality gates: pnpm test, pnpm lint, pnpm build..."
docker run --rm \
    -v "$PWD/frontend":/workspace -w /workspace \
    -e HOME=/tmp \
    "$NODE_IMAGE" \
    sh -c "
        set -e
        corepack enable
        corepack prepare pnpm@9 --activate
        pnpm config set store-dir /tmp/pnpm-store
        pnpm install --frozen-lockfile
        pnpm test
        pnpm lint
        pnpm build
    "

echo "All quality gates passed."
