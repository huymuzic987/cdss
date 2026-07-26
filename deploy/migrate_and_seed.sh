#!/usr/bin/env bash
# Starts the database container, wipes it completely, rebuilds the schema
# from Alembic migrations, then loads backups/seed.sql.
#
# The schema changes frequently during development, so every deploy resets
# the database to a known state instead of trying to reconcile drift:
#   1. DROP SCHEMA public CASCADE / CREATE SCHEMA public - wipes all tables,
#      data and types.
#   2. `alembic upgrade head` - rebuilds the schema from scratch.
#   3. backups/seed.sql - reloads decision trees and medicines reference
#      data (idempotent INSERTs with ON CONFLICT resolution).
#
# This intentionally discards any data that only existed in the live
# database (not in seed.sql) on every pipeline run.
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

# Make a backup copy of seed.sql before DB wipe if not already created
if [ -f "backups/seed.sql" ] && [ ! -f "backups/seed.sql.bak" ]; then
    echo "Creating backup of seed.sql before DB wipe..."
    cp backups/seed.sql backups/seed.sql.bak
fi

echo "Wiping database..."
$COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "Applying Alembic migrations..."
$COMPOSE run --rm backend alembic upgrade head

echo "Seeding data from backups/seed.sql..."
if ! $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/seed.sql; then
    echo "ERROR: Seeding data from backups/seed.sql failed!"
    if [ -f "backups/seed.sql.bak" ]; then
        echo "Reverting database back to previous working seed.sql file copy..."
        $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        $COMPOSE run --rm backend alembic upgrade head
        echo "Applying previous working seed.sql copy..."
        $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/seed.sql.bak
        cp backups/seed.sql.bak backups/seed.sql
        echo "Database successfully reverted to previous working seed data."
    else
        echo "No previous working seed.sql copy found to revert."
    fi
    exit 1
fi
