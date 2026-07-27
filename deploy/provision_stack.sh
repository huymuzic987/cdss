#!/usr/bin/env bash
# Builds and migrates a brand-new, fully isolated stack (db + backend) for
# this deploy version, side by side with whatever stack is currently live.
#
# The live stack is never touched here -- everything happens in a new
# `cdss-<version>` compose project with its own containers/network/volume.
# If anything in this script fails, nothing has been promoted and the
# currently-running version keeps serving traffic untouched.
#
# Frontend is deliberately NOT started here: only one stack can bind the
# public APP_PORT at a time on this single host, so frontend only comes up
# in promote_stack.sh, after the old stack has been stopped.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

VERSION="${1:?usage: provision_stack.sh <version>}"
export VERSION
PROJECT="cdss-${VERSION}"
resolve_compose "$PROJECT"

set -a
source .env
set +a

echo "Provisioning new stack ${PROJECT}..."
$COMPOSE up -d db

echo "Waiting for database to be ready..."
for i in $(seq 1 24); do
    if $COMPOSE exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        break
    fi
    sleep 5
done

echo "Applying Alembic migrations..."
$COMPOSE run --rm --build backend alembic upgrade head

echo "Seeding data from backups/seed.sql..."
$COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/seed.sql

echo "Starting backend..."
$COMPOSE up -d --build backend

echo "Waiting for backend to report healthy..."
for i in $(seq 1 12); do
    if $COMPOSE exec -T backend curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend healthy for ${PROJECT}."
        exit 0
    fi
    echo "Attempt $i failed. Waiting 5s..."
    sleep 5
done

echo "ERROR: backend never became healthy for ${PROJECT}"
$COMPOSE logs --tail 50 backend
exit 1
