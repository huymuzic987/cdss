#!/usr/bin/env bash
# Starts the given build, health-checks it, and rolls back to the last
# known-good build on failure. Runs on the deploy target, invoked over SSH
# by the Jenkinsfile's "Deploy & Health Check" stage.
#
# Usage: rollout.sh <build_number> <app_port>
set -euo pipefail

BUILD_NUMBER="$1"
APP_PORT="$2"
APP_NAME="cdss"
COMPOSE="docker compose -f docker-compose.prod.yml"
LAST_GOOD_FILE=".last_good_tag"

wait_healthy() {
    for i in $(seq 1 12); do
        if curl -s -f -L "http://localhost:${APP_PORT}/" > /dev/null 2>&1 \
            && $COMPOSE exec -T backend curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
            return 0
        fi
        echo "Attempt $i failed. Waiting 5s..."
        sleep 5
    done
    return 1
}

echo "Starting new containers (tag ${BUILD_NUMBER})..."
IMAGE_TAG="$BUILD_NUMBER" $COMPOSE up -d db backend frontend

if wait_healthy; then
    echo "cdss healthy on build ${BUILD_NUMBER}"
    echo "$BUILD_NUMBER" > "$LAST_GOOD_FILE"
    docker tag "${APP_NAME}-backend:${BUILD_NUMBER}" "${APP_NAME}-backend:latest"
    docker tag "${APP_NAME}-frontend:${BUILD_NUMBER}" "${APP_NAME}-frontend:latest"
    exit 0
fi

echo "Health check failed after 60 seconds - rolling back"
$COMPOSE logs --tail 50 backend frontend || true

if [ -f "$LAST_GOOD_FILE" ]; then
    PREV="$(cat "$LAST_GOOD_FILE")"
    echo "Rolling back to previously good build ${PREV}..."
    IMAGE_TAG="$PREV" $COMPOSE up -d db backend frontend

    if wait_healthy; then
        echo "Rolled back to build ${PREV} successfully; production is up on the previous version."
    else
        echo "Rollback ALSO failed health checks. Manual intervention required."
        $COMPOSE logs --tail 50 backend frontend || true
    fi
else
    echo "No previous good build recorded (first deploy) - nothing to roll back to."
fi

exit 1
