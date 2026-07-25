#!/usr/bin/env bash
# Waits for the frontend (public) and backend (internal) to report healthy.
# Usage: health_check.sh <app_port>
set -euo pipefail
source "$(dirname "$0")/lib.sh"
resolve_compose

APP_PORT="$1"

for i in $(seq 1 12); do
    if curl -s -f -L "http://localhost:${APP_PORT}/" > /dev/null 2>&1 \
        && $COMPOSE exec -T backend curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "cdss healthy on port ${APP_PORT}"
        exit 0
    fi
    echo "Attempt $i failed. Waiting 5s..."
    sleep 5
done

echo "Health check failed after 60 seconds"
$COMPOSE logs --tail 50 backend frontend
exit 1
