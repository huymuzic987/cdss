#!/usr/bin/env bash
# Keeps the 5 most recent numbered image tags per service (for rollback)
# and removes older ones plus any dangling images. Runs on the deploy
# target, invoked over SSH by the Jenkinsfile's "Cleanup Old Images" stage.
set -euo pipefail

APP_NAME="cdss"

for img in "${APP_NAME}-backend" "${APP_NAME}-frontend"; do
    docker images --format '{{.Tag}}' "$img" \
        | grep -E '^[0-9]+$' \
        | sort -rn \
        | tail -n +6 \
        | xargs -r -I{} docker rmi "${img}:{}" || true
done

docker image prune -f
