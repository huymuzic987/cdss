#!/usr/bin/env bash
# Promotes a provisioned stack (see provision_stack.sh) to live.
#
# Stops the previously-live stack (kept, not removed -- see
# prune_old_stacks.sh for retention/cleanup), starts the new stack's
# frontend now that the public port is free, then runs the full health
# check. If that final check fails, the new frontend is stopped again and
# whatever was stopped for the port handover is restarted, so the site is
# back up within one health-check cycle instead of staying down.
#
# Records the live version in deploy/.current_version on success -- that
# file is server-local state, not part of the repo (see the Jenkinsfile's
# rsync excludes), and is how this script and prune_old_stacks.sh know
# which stack is live vs. an old rollback candidate.
#
# deploy/.current_version is a bookkeeping hint, not the source of truth for
# "what currently holds the public port" -- it doesn't exist yet on the
# first deploy after switching to this blue/green flow (or if it ever drifts
# out of sync), so whatever container is actually bound to APP_PORT is found
# and stopped directly by container ID as a second, authoritative check.
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

stop_old_stack() {
    if [ -n "$OLD_VERSION" ] && [ "$OLD_VERSION" != "$NEW_VERSION" ]; then
        echo "Stopping previous stack cdss-${OLD_VERSION}..."
        ( export VERSION="$OLD_VERSION"; resolve_compose "cdss-${OLD_VERSION}"; $COMPOSE stop )
    fi
}

restart_old_stack() {
    if [ -n "$OLD_VERSION" ] && [ "$OLD_VERSION" != "$NEW_VERSION" ]; then
        echo "Restarting previous stack cdss-${OLD_VERSION}..."
        ( export VERSION="$OLD_VERSION"; resolve_compose "cdss-${OLD_VERSION}"; $COMPOSE start )
    fi
}

find_port_containers() {
    # Matches the "0.0.0.0:3001->80/tcp, :::3001->80/tcp" style Ports column
    # -- avoids relying on the `docker ps --filter publish=`, which isn't
    # available on older Docker versions.
    docker ps --format '{{.ID}} {{.Ports}}' | awk -v port=":${APP_PORT}->" '$0 ~ port {print $1}'
}

start_backup_service() {
    local backup_container=""

    echo "Starting daily database backup service..."
    if ! $COMPOSE up -d backup; then
        return 1
    fi

    for i in $(seq 1 5); do
        backup_container="$($COMPOSE ps -q backup)"
        if [ -n "$backup_container" ] \
            && [ "$(docker inspect -f '{{.State.Running}}' "$backup_container")" = "true" ]; then
            return 0
        fi
        sleep 2
    done

    echo "ERROR: daily database backup service did not stay running." >&2
    $COMPOSE logs --tail 50 backup
    return 1
}

stop_old_stack

PORT_CONTAINERS="$(find_port_containers)"
if [ -n "$PORT_CONTAINERS" ]; then
    echo "Stopping container(s) still bound to port ${APP_PORT}: ${PORT_CONTAINERS}"
    docker stop $PORT_CONTAINERS
fi

resolve_compose "$NEW_PROJECT"
echo "Starting frontend for ${NEW_PROJECT}..."
$COMPOSE up -d --no-build frontend

echo "Running health check..."
for i in $(seq 1 12); do
    if curl -s -f -L "http://localhost:${APP_PORT}/" > /dev/null 2>&1 \
        && $COMPOSE exec -T backend curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "${NEW_PROJECT} healthy on port ${APP_PORT}"
        if start_backup_service; then
            echo "$NEW_VERSION" > "$VERSION_FILE"
            exit 0
        fi
        break
    fi
    echo "Attempt $i failed. Waiting 5s..."
    sleep 5
done

echo "ERROR: ${NEW_PROJECT} failed health check after promotion."
$COMPOSE logs --tail 50 backend frontend

echo "Stopping the broken new frontend to free the port..."
$COMPOSE stop frontend

if [ -n "$PORT_CONTAINERS" ]; then
    echo "Restarting previously-stopped container(s): ${PORT_CONTAINERS}"
    docker start $PORT_CONTAINERS
else
    restart_old_stack
fi

exit 1
