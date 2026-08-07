#!/usr/bin/env bash
set -e

version="${1:?Usage: apply_contributions.sh <version>}"
script_dir="$(dirname "$(readlink -f "$0")")"
release_dir="$(dirname "$script_dir")"
cd "$release_dir"

chmod +x deploy/lib.sh
source deploy/lib.sh

resolve_compose "cdss-${version}"

POSTGRES_USER="$(dotenv_require .env POSTGRES_USER)"
POSTGRES_DB="$(dotenv_require .env POSTGRES_DB)"

if [ -f contributions.sql ] && [ -s contributions.sql ]; then
    $COMPOSE exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < contributions.sql
    rm -f contributions.sql
fi
