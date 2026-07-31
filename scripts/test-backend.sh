#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Backend unit tests (uv run pytest -m 'not database')"
uv run pytest -m "not database"

ENV_TEST_FILE=".env.test"
DB_HOST="localhost"
DB_PORT="54321"

if [[ ! -f "$ENV_TEST_FILE" ]]; then
  echo
  echo "==> Skipping seeded database tests: $ENV_TEST_FILE not found."
  echo "    Copy .env.test.example to .env.test to enable them."
  exit 0
fi

# Pull host/port out of DATABASE_URL if present, otherwise keep the compose.yaml defaults above.
if url_line=$(grep -E '^DATABASE_URL=' "$ENV_TEST_FILE" | tail -1); then
  url="${url_line#DATABASE_URL=}"
  if [[ "$url" =~ @([^:/]+):([0-9]+) ]]; then
    DB_HOST="${BASH_REMATCH[1]}"
    DB_PORT="${BASH_REMATCH[2]}"
  fi
fi

db_reachable() {
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h "$DB_HOST" -p "$DB_PORT" -t 2 >/dev/null 2>&1
  else
    (exec 3<>"/dev/tcp/$DB_HOST/$DB_PORT") >/dev/null 2>&1
  fi
}

echo
if db_reachable; then
  echo "==> Postgres reachable at $DB_HOST:$DB_PORT -- running seeded database tests"
  uv run pytest -m database
else
  echo "==> Skipping seeded database tests: Postgres not reachable at $DB_HOST:$DB_PORT."
  echo "    Start it with: docker compose up -d postgres"
fi
