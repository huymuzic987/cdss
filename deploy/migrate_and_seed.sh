#!/usr/bin/env bash
# Starts the database container, applies Alembic migrations, then restores
# backups/cdss_prod.sql the first time the database is empty.
#
# cdss_prod.sql is a from-scratch dump (plain CREATE TABLE, wrapped in one
# transaction, sets alembic_version) meant for an EMPTY database - re-running
# it against an already-seeded database would fail outright, so this only
# applies it once. It runs BEFORE `alembic upgrade head` so any migrations
# newer than the dump's revision still apply on top of it afterward.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
resolve_compose

set -a
source .env
set +a

echo "Starting database..."
$COMPOSE up -d db

echo "Waiting for database to be ready..."
for i in $(seq 1 24); do
    if $COMPOSE exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        break
    fi
    sleep 5
done

existing="$($COMPOSE exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select to_regclass('public.decision_trees')")"
if [ -z "$existing" ]; then
    echo "Fresh database detected - restoring backups/cdss_prod.sql..."
    $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/cdss_prod.sql
else
    echo "decision_trees already exists - skipping backups/cdss_prod.sql (already seeded)."
fi

echo "Applying Alembic migrations..."
$COMPOSE run --rm backend uv run alembic upgrade head
