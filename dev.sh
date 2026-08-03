#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "========================================"
echo "  CDSS Efficient Dev Server Launcher    "
echo "========================================"

echo ""
echo "[1/3] Starting PostgreSQL container..."

start_postgres() {
    if command -v docker >/dev/null 2>&1; then
        if docker compose version >/dev/null 2>&1; then
            docker compose up -d postgres 2>/dev/null || docker compose up -d 2>/dev/null && return 0
        elif command -v docker-compose >/dev/null 2>&1; then
            docker-compose up -d postgres 2>/dev/null || docker-compose up -d 2>/dev/null && return 0
        fi
    fi

    # Fallback to docker.exe if running inside WSL connecting to Docker Desktop
    if command -v docker.exe >/dev/null 2>&1; then
        docker.exe compose up -d postgres 2>/dev/null || docker.exe compose up -d 2>/dev/null && return 0
    fi

    return 1
}

start_postgres || echo "Warning: Docker compose command failed, checking if DB is already running..."

echo "[2/3] Waiting for database connection on port 54321..."
until uv run python -c "import psycopg2; from backups.dump import _database_url; conn=psycopg2.connect(_database_url())" 2>/dev/null; do
    sleep 1
done
echo "-> Database connection established!"

echo ""
echo "[3/3] Checking database seed status..."
uv run python scripts/ensure_seed.py "$@"

echo ""
echo "========================================"
echo "  Database Ready! Starting Servers...   "
echo "  Backend  : http://localhost:8000      "
echo "  Frontend : http://localhost:5173      "
echo "========================================"

trap 'kill $(jobs -p) 2>/dev/null || true' EXIT

uv run uvicorn cdss.main:app --reload --reload-dir src &
pnpm --prefix frontend dev &
wait
