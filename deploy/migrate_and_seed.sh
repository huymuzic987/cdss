#!/usr/bin/env bash
# Starts the database container, applies Alembic migrations, then restores
# backups/cdss_prod.sql and backups/medicines.sql the first time each is
# empty.
#
# cdss_prod.sql is a from-scratch dump (plain CREATE TABLE, wrapped in one
# transaction, sets alembic_version) meant for an EMPTY database - re-running
# it against an already-seeded database would fail outright, so this only
# applies it once. It runs BEFORE `alembic upgrade head` so any migrations
# newer than the dump's revision still apply on top of it afterward.
#
# medicines.sql is a bare INSERT with no ON CONFLICT handling (same
# re-run-fails-outright constraint), and it targets the medicines table,
# which is created by a migration rather than by cdss_prod.sql - so it runs
# AFTER `alembic upgrade head`, once that table is guaranteed to exist.
#
# Both restores go straight through `psql` against the already-running db
# container (same as the health-check/readiness calls below) rather than
# spinning up a throwaway backend container for it - cheaper and there's
# nothing backend-specific about loading a SQL file.
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
$COMPOSE run --rm backend alembic upgrade head

medicine_count="$($COMPOSE exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from medicines")"
if [ "$medicine_count" -eq 0 ]; then
    echo "medicines table is empty - restoring backups/medicines.sql..."
    $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/medicines.sql
else
    echo "medicines table already has $medicine_count rows - skipping backups/medicines.sql."
fi
