#!/usr/bin/env bash
# Provisions an isolated stack for this deploy version. When a live version
# exists, its PostgreSQL database is copied with a transactionally-consistent
# pg_dump stream while production continues serving traffic. The clone is
# then migrated and seeded without overwriting tree_layouts.
#
# The live stack is never touched here -- everything happens in a new
# `cdss-<version>` compose project with its own containers/network/volume.
# If anything in this script fails, nothing has been promoted and the
# currently-running version keeps serving traffic untouched.
#
# The frontend has no host port. It starts and becomes healthy alongside the
# backend while the stable router continues sending traffic to the old release.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

VERSION="${1:?usage: provision_stack.sh <version>}"
export VERSION
PROJECT="cdss-${VERSION}"
VERSION_FILE="deploy/state/.current_version"
OLD_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"
resolve_compose "$PROJECT"

validate_dotenv_file .env
POSTGRES_USER="$(dotenv_require .env POSTGRES_USER)"
POSTGRES_DB="$(dotenv_require .env POSTGRES_DB)"

echo "Provisioning new stack ${PROJECT}..."
run_timed "candidate-database-start" $COMPOSE up -d db

echo "Waiting for database to be ready..."
db_ready_started_at="$(date +%s)"
db_ready=false
for i in $(seq 1 120); do
    if $COMPOSE exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        db_ready=true
        break
    fi
    sleep 1
done
if [ "$db_ready" != "true" ]; then
    printf 'CDSS_TIMING\tcandidate-database-ready\t%s\t1\n' \
        "$(($(date +%s) - db_ready_started_at))"
    echo "ERROR: database for ${PROJECT} did not become ready" >&2
    $COMPOSE logs --tail 50 db
    exit 1
fi
printf 'CDSS_TIMING\tcandidate-database-ready\t%s\t0\n' \
    "$(($(date +%s) - db_ready_started_at))"

if [ -n "$OLD_VERSION" ] && [ "$OLD_VERSION" != "$VERSION" ]; then
    echo "Cloning live database from cdss-${OLD_VERSION} into ${PROJECT}..."
    resolve_compose "cdss-${OLD_VERSION}"
    OLD_DB_CONTAINER="$($COMPOSE ps -q db)"
    if [ -z "$OLD_DB_CONTAINER" ] \
        || [ "$(docker inspect -f '{{.State.Running}}' "$OLD_DB_CONTAINER")" != "true" ]; then
        echo "ERROR: live database container for cdss-${OLD_VERSION} is not running" >&2
        exit 1
    fi

    container_env() {
        local key="$1"
        docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$OLD_DB_CONTAINER" \
            | sed -n "s/^${key}=//p" \
            | head -n 1
    }
    OLD_DB_USER="$(container_env POSTGRES_USER)"
    OLD_DB_NAME="$(container_env POSTGRES_DB)"
    if [ -z "$OLD_DB_USER" ] || [ -z "$OLD_DB_NAME" ]; then
        echo "ERROR: could not read credentials from cdss-${OLD_VERSION}" >&2
        exit 1
    fi
    if source_db_size_bytes="$(
        docker exec "$OLD_DB_CONTAINER" psql \
            --username="$OLD_DB_USER" \
            --dbname="$OLD_DB_NAME" \
            --tuples-only \
            --no-align \
            --command='SELECT pg_database_size(current_database());'
    )"; then
        printf 'CDSS_METRIC\tsource-database-size-bytes\t%s\n' "$source_db_size_bytes"
    else
        echo "WARNING: unable to measure source database size for the CI/CD baseline." >&2
    fi

    resolve_compose "$PROJECT"
    clone_live_database() {
        docker exec "$OLD_DB_CONTAINER" pg_dump \
            --username="$OLD_DB_USER" \
            --dbname="$OLD_DB_NAME" \
            --format=plain \
            --no-owner \
            --no-privileges \
            | $COMPOSE exec -T db psql \
                -v ON_ERROR_STOP=1 \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB"
    }
    run_timed "candidate-database-clone" clone_live_database
    SEED_MODE="preserve-layouts"
else
    echo "No live version recorded; initializing the first database from migrations."
    SEED_MODE="all"
fi

echo "Applying Alembic migrations..."
run_timed "candidate-alembic-migration" \
    $COMPOSE run --rm --no-deps backend alembic upgrade head

mapfile -t EXPECTED_HEADS < <(
    $COMPOSE run --rm --no-deps backend alembic heads \
        | awk '/\(head\)$/ {print $1}'
)
if [ "${#EXPECTED_HEADS[@]}" -ne 1 ]; then
    echo "ERROR: expected exactly one Alembic head, found ${#EXPECTED_HEADS[@]}." >&2
    exit 1
fi
EXPECTED_HEAD="${EXPECTED_HEADS[0]}"

LAYOUT_FINGERPRINT=""
if [ "$SEED_MODE" = "preserve-layouts" ]; then
    LAYOUT_FINGERPRINT="$(
        $COMPOSE exec -T db psql \
            -v ON_ERROR_STOP=1 \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            --tuples-only \
            --no-align \
            --command="SELECT count(*)::text || ':' ||
                md5(COALESCE(string_agg(
                    id::text || ':' || node_positions::text || ':' || edge_layouts::text,
                    '|' ORDER BY id
                ), ''))
                FROM tree_layouts;"
    )"
fi

echo "Seeding data from backups/seed.sql (mode: ${SEED_MODE})..."
seed_candidate_database() {
    bash deploy/seed_database.sh "$SEED_MODE" backups/seed.sql \
        | $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
}
run_timed "candidate-database-seed" seed_candidate_database

echo "Validating candidate schema, seed invariants, links, and preserved layouts..."
validate_candidate_database() {
    bash deploy/validate_candidate_db.sh \
        "$EXPECTED_HEAD" "$SEED_MODE" "$LAYOUT_FINGERPRINT" \
        | $COMPOSE exec -T db psql \
            -v ON_ERROR_STOP=1 \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB"
}
run_timed "candidate-database-validation" validate_candidate_database

echo "Starting backend and private frontend..."
run_timed "candidate-services-start" \
    $COMPOSE up -d --no-build backend frontend

echo "Waiting for backend and frontend to report healthy..."
candidate_health_started_at="$(date +%s)"
for i in $(seq 1 60); do
    if $COMPOSE exec -T backend curl -s -f http://localhost:8000/health > /dev/null 2>&1 \
        && $COMPOSE exec -T frontend wget -qO- http://127.0.0.1/ > /dev/null 2>&1; then
        printf 'CDSS_TIMING\tcandidate-services-healthy\t%s\t0\n' \
            "$(($(date +%s) - candidate_health_started_at))"
        echo "Backend and frontend healthy for ${PROJECT}."
        exit 0
    fi
    echo "Attempt $i failed. Waiting 1s..."
    sleep 1
done

printf 'CDSS_TIMING\tcandidate-services-healthy\t%s\t1\n' \
    "$(($(date +%s) - candidate_health_started_at))"
echo "ERROR: backend or frontend never became healthy for ${PROJECT}"
$COMPOSE logs --tail 50 backend frontend
exit 1
