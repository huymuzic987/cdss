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

RAW_CI_RUN_ID="${BUILD_TAG:-local-$$}"
RAW_CI_JOB_ID="${JOB_NAME:-cdss}"
CI_RUN_ID="$(
    printf '%s' "$RAW_CI_RUN_ID" \
        | tr '[:upper:]' '[:lower:]' \
        | tr -c 'a-z0-9_.-' '-' \
        | cut -c1-48
)"
CI_JOB_ID="$(
    printf '%s' "$RAW_CI_JOB_ID" \
        | tr '[:upper:]' '[:lower:]' \
        | tr -c 'a-z0-9_.-' '-' \
        | cut -c1-48
)"
NETWORK="cdss-ci-${CI_RUN_ID}-net"
POSTGRES_CONTAINER="cdss-ci-${CI_RUN_ID}-postgres"
UV_CACHE_VOLUME="cdss-ci-uv-cache-py312"
UV_ENV_VOLUME="cdss-ci-uv-env-py312"
PNPM_STORE_VOLUME="cdss-ci-pnpm-store-v9"
PNPM_MODULES_VOLUME="cdss-ci-node-modules-v9"
COREPACK_VOLUME="cdss-ci-corepack-pnpm9"
PYRIGHT_CACHE_VOLUME="cdss-ci-pyright-node-py312"

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

# Pyright installs a Node.js runtime whose Linux binary requires
# libatomic.so.1. The full Bookworm image provides it; the slim variant does
# not, causing Pyright to exit 127 before type checking starts.
UV_IMAGE="ghcr.io/astral-sh/uv:python3.12-bookworm"
# Vite 8/jsdom 30/undici 8 require modern Node APIs that are unavailable in
# Node 20 (notably worker_threads.markAsUncloneable). Pin the tested runtime
# instead of following a moving major tag.
NODE_IMAGE="node:24.18.1-alpine"
PNPM_VERSION="9.15.9"
CDSS_TIMING_FILE="${CDSS_TIMING_FILE:-$PWD/.ci-reports/timings.tsv}"

# Emit tab-separated timing records that can be copied from the Jenkins log
# into the deployment baseline. Keep this deliberately log-only for now so
# measurement cannot make an otherwise healthy quality gate fail.
timed() {
    local gate_name="$1"
    shift
    local started_at finished_at elapsed status
    started_at="$(date +%s)"
    echo "=== Timing start: ${gate_name} ==="
    if "$@"; then
        status=0
    else
        status=$?
    fi
    finished_at="$(date +%s)"
    elapsed=$((finished_at - started_at))
    printf 'CDSS_TIMING\t%s\t%s\t%s\n' "$gate_name" "$elapsed" "$status"
    printf '%s\t%s\t%s\n' "$gate_name" "$elapsed" "$status" \
        >> "$CDSS_TIMING_FILE" || true
    return "$status"
}

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

# A hard-killed build can leave its detached PostgreSQL container and network.
# Builds of this Jenkins job are non-concurrent, so job-scoped leftovers are
# safe to remove before this build creates its own uniquely named resources.
if [ -n "${BUILD_TAG:-}" ]; then
    while IFS= read -r stale_container; do
        [ -z "$stale_container" ] \
            || docker rm -f "$stale_container" > /dev/null 2>&1 \
            || true
    done < <(docker ps -aq --filter "label=io.cdss.ci.job=$CI_JOB_ID")
    while IFS= read -r stale_network; do
        [ -z "$stale_network" ] \
            || docker network rm "$stale_network" > /dev/null 2>&1 \
            || true
    done < <(docker network ls -q --filter "label=io.cdss.ci.job=$CI_JOB_ID")
fi

# Defensive cleanup also handles a retry using the same Jenkins build tag.
cleanup

mkdir -p .ci-reports/backend frontend/.ci-reports

echo "Preparing persistent dependency caches..."
docker volume create "$UV_CACHE_VOLUME" > /dev/null
docker volume create "$UV_ENV_VOLUME" > /dev/null
docker volume create "$PNPM_STORE_VOLUME" > /dev/null
docker volume create "$PNPM_MODULES_VOLUME" > /dev/null
docker volume create "$COREPACK_VOLUME" > /dev/null
docker volume create "$PYRIGHT_CACHE_VOLUME" > /dev/null
docker run --rm \
    -v "$UV_CACHE_VOLUME":/uv-cache \
    -v "$UV_ENV_VOLUME":/venv \
    -v "$PYRIGHT_CACHE_VOLUME":/pyright-cache \
    -e CACHE_UID="$HOST_UID" \
    -e CACHE_GID="$HOST_GID" \
    alpine:3 \
    sh -c '
        for cache_dir in /uv-cache /venv /pyright-cache; do
            if [ "$(stat -c %u "$cache_dir")" != "$CACHE_UID" ]; then
                chown -R "$CACHE_UID:$CACHE_GID" "$cache_dir"
            fi
        done
    '

docker network create \
    --label "io.cdss.ci.job=$CI_JOB_ID" \
    --label "io.cdss.ci.run=$CI_RUN_ID" \
    "$NETWORK" > /dev/null

echo "Starting disposable PostgreSQL for the database-backed test suite..."
timed "test-postgres-start" docker run -d --name "$POSTGRES_CONTAINER" \
    --label "io.cdss.ci.job=$CI_JOB_ID" \
    --label "io.cdss.ci.run=$CI_RUN_ID" \
    --network "$NETWORK" --network-alias postgres \
    -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB="$PG_ADMIN_DB" \
    postgres:16 -p "$TEST_DB_PORT"

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

echo "Generating deterministic pregnancy FHIR catalogs..."
timed "pregnancy-fhir-catalog-and-migration" docker run --rm --network "$NETWORK" \
    -v "$PWD":/workspace -w /workspace \
    -v "$UV_CACHE_VOLUME":/uv-cache \
    -v "$UV_ENV_VOLUME":/venv \
    -e DATABASE_URL="$TEST_DATABASE_URL" \
    -e CDSS_TIMING_FILE=/workspace/.ci-reports/timings.tsv \
    -e HOME=/tmp -e UV_CACHE_DIR=/uv-cache -e UV_PROJECT_ENVIRONMENT=/venv \
    --user "${HOST_UID}:${HOST_GID}" \
    "$UV_IMAGE" \
    sh -c "
        set -e
        timed() {
            gate_name=\"\$1\"
            shift
            started_at=\"\$(date +%s)\"
            if \"\$@\"; then status=0; else status=\$?; fi
            elapsed=\$((\$(date +%s) - started_at))
            printf 'CDSS_TIMING\\t%s\\t%s\\t%s\\n' \"\$gate_name\" \"\$elapsed\" \"\$status\"
            printf '%s\\t%s\\t%s\\n' \"\$gate_name\" \"\$elapsed\" \"\$status\" \
                >> \"\$CDSS_TIMING_FILE\" || true
            return \"\$status\"
        }
        timed catalog-dependency-sync uv sync --frozen
        timed pregnancy-fhir-generation uv run python scripts/generate_pregnancy_fhir_presets.py
        timed test-schema-migration uv run alembic upgrade head
    "
echo "Pregnancy FHIR catalogs generated; disposable database migrated to head."

echo "Seeding the disposable test database (trees, medicines, symptoms reference data)..."
seed_test_database() {
    docker exec -i "$POSTGRES_CONTAINER" \
        psql -p "$TEST_DB_PORT" -U "$PG_USER" -d "$TEST_DB_NAME" \
        < backups/seed.sql > /dev/null
}
timed "test-database-seed" seed_test_database

run_backend_quality_gates() {
    echo "Running backend quality gates: pytest, ruff check, ruff format --check, pyright..."
    timed "backend-quality-gates-total" docker run --rm --network "$NETWORK" \
    -v "$PWD":/workspace -w /workspace \
    -v "$UV_CACHE_VOLUME":/uv-cache \
    -v "$UV_ENV_VOLUME":/venv \
    -v "$PYRIGHT_CACHE_VOLUME":/pyright-cache \
    -e DATABASE_URL="$TEST_DATABASE_URL" \
    -e CDSS_TIMING_FILE=/workspace/.ci-reports/timings.tsv \
    -e HOME=/tmp -e UV_CACHE_DIR=/uv-cache -e UV_PROJECT_ENVIRONMENT=/venv \
    -e PYRIGHT_PYTHON_CACHE_DIR=/pyright-cache \
    --user "${HOST_UID}:${HOST_GID}" \
    "$UV_IMAGE" \
    sh -c "
        set -e
        timed() {
            gate_name=\"\$1\"
            shift
            started_at=\"\$(date +%s)\"
            if \"\$@\"; then status=0; else status=\$?; fi
            elapsed=\$((\$(date +%s) - started_at))
            printf 'CDSS_TIMING\\t%s\\t%s\\t%s\\n' \"\$gate_name\" \"\$elapsed\" \"\$status\"
            printf '%s\\t%s\\t%s\\n' \"\$gate_name\" \"\$elapsed\" \"\$status\" \
                >> \"\$CDSS_TIMING_FILE\" || true
            return \"\$status\"
        }
        timed backend-dependency-sync uv sync --frozen
        # Pytest and Pyright are independent and dominate this branch's
        # runtime. Run them together after the shared environment is synced;
        # The former runtime preflight bootstrapped the same Node runtime
        # twice on cold agents without providing an additional gate.
        timed backend-pytest uv run pytest \
            --junitxml=.ci-reports/backend/junit.xml \
            --cov=cdss \
            --cov-report=term-missing \
            --cov-report=xml:.ci-reports/backend/coverage.xml &
        pytest_pid=\$!
        timed backend-pyright uv run pyright &
        pyright_pid=\$!

        pytest_status=0
        pyright_status=0
        if wait \"\$pytest_pid\"; then :; else pytest_status=\$?; fi
        if wait \"\$pyright_pid\"; then :; else pyright_status=\$?; fi
        if [ \"\$pytest_status\" -ne 0 ] || [ \"\$pyright_status\" -ne 0 ]; then
            exit 1
        fi

        timed backend-ruff-check uv run ruff check
        timed backend-ruff-format uv run ruff format --check
    "
}

run_frontend_quality_gates() {
    echo "Running frontend quality gates: Vitest, Oxlint, TypeScript, Vite build..."
    timed "frontend-quality-gates-total" docker run --rm \
    -v "$PWD/frontend":/workspace -w /workspace \
    -v "$PWD/deploy/run_frontend_quality_gates.sh":/quality-gate.sh:ro \
    -v "$PNPM_STORE_VOLUME":/pnpm/store \
    -v "$PNPM_MODULES_VOLUME":/workspace/node_modules \
    -v "$COREPACK_VOLUME":/corepack \
    -e HOME=/tmp \
    -e COREPACK_HOME=/corepack \
    -e PNPM_VERSION="$PNPM_VERSION" \
    -e PNPM_STORE_DIR=/pnpm/store \
    -e CDSS_TIMING_FILE=/workspace/.ci-reports/timings.tsv \
    "$NODE_IMAGE" \
    sh /quality-gate.sh
}

echo "Running backend and frontend quality gates concurrently..."
run_backend_quality_gates &
backend_gate_pid=$!
run_frontend_quality_gates &
frontend_gate_pid=$!

backend_gate_status=0
frontend_gate_status=0
if wait "$backend_gate_pid"; then
    echo "Backend quality-gate branch passed."
else
    backend_gate_status=$?
    echo "ERROR: backend quality-gate branch failed with exit code $backend_gate_status." >&2
fi
if wait "$frontend_gate_pid"; then
    echo "Frontend quality-gate branch passed."
else
    frontend_gate_status=$?
    echo "ERROR: frontend quality-gate branch failed with exit code $frontend_gate_status." >&2
fi

if [ "$backend_gate_status" -ne 0 ] || [ "$frontend_gate_status" -ne 0 ]; then
    exit 1
fi

echo "All quality gates passed."
