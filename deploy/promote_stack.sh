#!/usr/bin/env bash
# Promotes a provisioned stack (see provision_stack.sh) to live.
#
# Stops the previously-live stack (kept, not removed -- see
# prune_old_stacks.sh for retention/cleanup), starts the new stack's
# frontend now that the public port is free, then runs the full health
# check. If that final check fails, the new frontend is stopped again and
# the old stack is restarted immediately, so the site is back up within
# one health-check cycle instead of staying down.
#
# Records the live version in deploy/.current_version on success -- that
# file is server-local state, not part of the repo (see the Jenkinsfile's
# rsync excludes), and is how this script and prune_old_stacks.sh know
# which stack is live vs. an old rollback candidate.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

NEW_VERSION="${1:?usage: promote_stack.sh <new_version>}"
NEW_PROJECT="cdss-${NEW_VERSION}"
VERSION_FILE="deploy/.current_version"

export VERSION="$NEW_VERSION"
resolve_compose "$NEW_PROJECT"

set -a
source .env
set +a

OLD_VERSION=""
if [ -f "$VERSION_FILE" ]; then
    OLD_VERSION="$(cat "$VERSION_FILE")"
fi

stop_old() {
    if [ -n "$OLD_VERSION" ] && [ "$OLD_VERSION" != "$NEW_VERSION" ]; then
        echo "Stopping previous stack cdss-${OLD_VERSION}..."
        ( export VERSION="$OLD_VERSION"; resolve_compose "cdss-${OLD_VERSION}"; $COMPOSE stop )
    fi
}

restart_old() {
    if [ -n "$OLD_VERSION" ] && [ "$OLD_VERSION" != "$NEW_VERSION" ]; then
        echo "Restarting previous stack cdss-${OLD_VERSION} to restore service..."
        ( export VERSION="$OLD_VERSION"; resolve_compose "cdss-${OLD_VERSION}"; $COMPOSE start )
    fi
}

stop_old

resolve_compose "$NEW_PROJECT"
echo "Starting frontend for ${NEW_PROJECT}..."
$COMPOSE up -d --build frontend

echo "Running health check..."
for i in $(seq 1 12); do
    if curl -s -f -L "http://localhost:${APP_PORT}/" > /dev/null 2>&1 \
        && $COMPOSE exec -T backend curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "${NEW_PROJECT} healthy on port ${APP_PORT}"
        echo "$NEW_VERSION" > "$VERSION_FILE"
        exit 0
    fi
    echo "Attempt $i failed. Waiting 5s..."
    sleep 5
done

echo "ERROR: ${NEW_PROJECT} failed health check after promotion."
$COMPOSE logs --tail 50 backend frontend

echo "Stopping the broken new frontend to free the port..."
$COMPOSE stop frontend

restart_old

exit 1
