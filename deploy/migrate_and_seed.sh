#!/usr/bin/env bash
# Starts the database container, applies Alembic migrations, then restores
# backups/backup.sql (or backups/seed.sql) the first time the database is empty.
#
# backup.sql is a from-scratch snapshot (DDL + data, sets alembic_version)
# meant for an EMPTY database - re-running it against an already-seeded
# database would fail outright, so this only applies it once on fresh DBs.
# It runs BEFORE `alembic upgrade head` so any migrations newer than the dump's
# revision still apply on top of it afterward.
#
# seed.sql contains pure data INSERT statements (no DDL schema) for decision
# trees and medicines reference data. It can be re-run after Alembic migrations
# if decision_trees is empty.
#
# Restores go straight through `psql` against the already-running db container
# rather than spinning up a throwaway backend container.
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
    echo "Fresh database detected - restoring backups/backup.sql..."
    $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/backup.sql
else
    echo "decision_trees table already exists - skipping backups/backup.sql."
fi

echo "Applying Alembic migrations..."
$COMPOSE run --rm backend alembic upgrade head

tree_count="$($COMPOSE exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from decision_trees")"
if [ "$tree_count" -eq 0 ]; then
    echo "decision_trees table is empty - seeding data from backups/seed.sql..."
    $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/seed.sql
else
    echo "decision_trees table already has $tree_count rows - skipping backups/seed.sql."
fi
