#!/usr/bin/env bash
# Applies backups/cdss.sql (decision trees + medicines) against the
# running database on every deploy, not just the first one - the file is
# the source of truth for this reference data, and it is expected to change
# over time.
#
# IMPORTANT: for this to succeed on anything but a from-scratch database,
# cdss.sql must itself be safe to re-run (e.g. DROP-then-CREATE, or
# CREATE TABLE IF NOT EXISTS paired with an idempotent data refresh such as
# TRUNCATE+INSERT or INSERT ... ON CONFLICT). Runs after `alembic upgrade
# head` so every table it touches - including medicines, which is created
# by a migration rather than by this file - already exists.
set -euo pipefail

set -a
source .env
set +a

COMPOSE="docker compose -f docker-compose.prod.yml"

echo "Applying backups/cdss.sql..."
$COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/cdss.sql
