#!/usr/bin/env bash
# Promotes an already-healthy private frontend without releasing the public
# host port. A stable nginx container owns APP_PORT for its entire lifetime.
#
# The router is a dedicated container with no Compose release labels. Nginx
# reloads are atomic, so existing connections finish on the old configuration
# while new connections use the selected release.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

NEW_VERSION="${1:?usage: promote_stack.sh <new_version> [promote|rollback|route-only]}"
MODE="${2:-promote}"
if [ "$MODE" != "promote" ] \
    && [ "$MODE" != "rollback" ] \
    && [ "$MODE" != "route-only" ]; then
    echo "ERROR: mode must be promote, rollback, or route-only." >&2
    exit 2
fi
NEW_PROJECT="cdss-${NEW_VERSION}"
VERSION_FILE="deploy/state/.current_version"
STATE_FILE="deploy/state/.deployment_state"
DRAIN_FILE="deploy/state/.router_drain_pending"
WRITE_LOCK_FILE="deploy/state/.write_lock"
ROUTER_NAME="cdss-router"
OLD_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"
OLD_GIT_COMMIT="$(
    sed -n 's/^git_commit=//p' "$STATE_FILE" 2>/dev/null | head -n 1 || true
)"
DEPLOY_GIT_COMMIT="${DEPLOY_GIT_COMMIT:-unknown}"

export VERSION="$NEW_VERSION"
resolve_compose "$NEW_PROJECT"

validate_dotenv_file .env
DOTENV_APP_PORT="$(dotenv_get .env APP_PORT || true)"
APP_PORT="${PUBLIC_APP_PORT:-${DOTENV_APP_PORT:-3000}}"

find_port_containers() {
    # Matches the "0.0.0.0:3001->80/tcp, :::3001->80/tcp" style Ports column.
    docker ps --format '{{.ID}} {{.Ports}}' \
        | awk -v port=":${APP_PORT}->" '$0 ~ port {print $1}'
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

NEW_FRONTEND_ID="$($COMPOSE ps -q frontend)"
if [ -z "$NEW_FRONTEND_ID" ] \
    || [ "$(docker inspect -f '{{.State.Running}}' "$NEW_FRONTEND_ID")" != "true" ]; then
    echo "ERROR: frontend for ${NEW_PROJECT} is not running." >&2
    exit 1
fi

NEW_NETWORK="$(
    docker inspect \
        -f '{{range $name, $settings := .NetworkSettings.Networks}}{{println $name}}{{end}}' \
        "$NEW_FRONTEND_ID" \
        | head -n 1
)"
if [ -z "$NEW_NETWORK" ]; then
    echo "ERROR: could not determine the network for ${NEW_PROJECT}." >&2
    exit 1
fi
NEW_FRONTEND_ALIAS="cdss-frontend-${NEW_VERSION}"

mapfile -t PORT_CONTAINERS < <(find_port_containers)
if [ "${#PORT_CONTAINERS[@]}" -gt 1 ]; then
    echo "ERROR: multiple containers are bound to APP_PORT ${APP_PORT}: ${PORT_CONTAINERS[*]}" >&2
    exit 1
fi

ROUTER_ID="$(docker ps -aq --filter "name=^/${ROUTER_NAME}$" | head -n 1)"
if [ -n "$ROUTER_ID" ]; then
    if [ "${#PORT_CONTAINERS[@]}" -eq 1 ] \
        && [ "${PORT_CONTAINERS[0]}" != "$ROUTER_ID" ]; then
        echo "ERROR: ${ROUTER_NAME} exists, but ${PORT_CONTAINERS[0]} owns APP_PORT ${APP_PORT}." >&2
        exit 1
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' "$ROUTER_ID")" != "true" ]; then
        echo "Starting stable router..."
        docker start "$ROUTER_ID" > /dev/null
    fi
elif [ "${#PORT_CONTAINERS[@]}" -eq 1 ]; then
    echo "ERROR: ${PORT_CONTAINERS[0]} owns APP_PORT ${APP_PORT}, but it is not ${ROUTER_NAME}." >&2
    echo "Refusing to adopt a release container as the stable router." >&2
    exit 1
else
    echo "Creating dedicated stable router on host port ${APP_PORT}..."
    docker run -d \
        --name "$ROUTER_NAME" \
        --restart unless-stopped \
        -p "${APP_PORT}:80" \
        nginx:1.27-alpine > /dev/null
    ROUTER_ID="$(docker inspect -f '{{.Id}}' "$ROUTER_NAME")"
fi

CONNECTED_NEW_NETWORK=false
PROMOTION_COMPLETE=false
OLD_CONFIG=""
NEW_CONFIG=""
STATE_TMP=""
VERSION_TMP=""
cleanup() {
    [ -z "$OLD_CONFIG" ] || rm -f "$OLD_CONFIG"
    [ -z "$NEW_CONFIG" ] || rm -f "$NEW_CONFIG"
    [ -z "$STATE_TMP" ] || rm -f "$STATE_TMP"
    [ -z "$VERSION_TMP" ] || rm -f "$VERSION_TMP"
    if [ "$PROMOTION_COMPLETE" != "true" ] \
        && [ "$CONNECTED_NEW_NETWORK" = "true" ]; then
        docker network disconnect "$NEW_NETWORK" "$ROUTER_NAME" > /dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

if ! docker inspect -f '{{range $name, $settings := .NetworkSettings.Networks}}{{println $name}}{{end}}' \
    "$ROUTER_NAME" | grep -Fxq "$NEW_NETWORK"; then
    echo "Connecting stable router to ${NEW_NETWORK}..."
    docker network connect "$NEW_NETWORK" "$ROUTER_NAME"
    CONNECTED_NEW_NETWORK=true
fi

# Check the release through the exact network path the router will use before
# touching its loaded nginx configuration.
if ! docker exec "$ROUTER_NAME" wget -qO- "http://${NEW_FRONTEND_ALIAS}/" > /dev/null 2>&1; then
    echo "ERROR: router cannot reach ${NEW_FRONTEND_ALIAS} on ${NEW_NETWORK}." >&2
    exit 1
fi

OLD_CONFIG="$(mktemp)"
NEW_CONFIG="$(mktemp)"

docker cp "${ROUTER_NAME}:/etc/nginx/conf.d/default.conf" "$OLD_CONFIG"
write_lock_enabled=false
[ ! -f "$WRITE_LOCK_FILE" ] || write_lock_enabled=true
bash deploy/render_router_config.sh \
    "$NEW_VERSION" \
    "$NEW_FRONTEND_ALIAS" \
    "$write_lock_enabled" \
    > "$NEW_CONFIG"

rollback_router() {
    echo "Restoring the previous router configuration..."
    docker cp "$OLD_CONFIG" "${ROUTER_NAME}:/etc/nginx/conf.d/default.conf"
    docker exec "$ROUTER_NAME" nginx -t
    docker exec "$ROUTER_NAME" nginx -s reload
}

# Replacing the file does not affect loaded workers. Only a successful
# nginx -s reload switches traffic, and nginx keeps old workers alive until
# their existing requests complete.
docker cp "$NEW_CONFIG" "${ROUTER_NAME}:/etc/nginx/conf.d/default.conf"
if ! docker exec "$ROUTER_NAME" nginx -t; then
    rollback_router
    exit 1
fi

echo "Atomically switching APP_PORT ${APP_PORT} to ${NEW_PROJECT}..."
docker exec "$ROUTER_NAME" nginx -s reload

promoted=false
for i in $(seq 1 10); do
    release_header="$(
        curl -sS -f -D - -o /dev/null "http://127.0.0.1:${APP_PORT}/" 2>/dev/null \
            | tr -d '\r' \
            | sed -n 's/^X-CDSS-Release: //p' \
            | tail -n 1 \
            || true
    )"
    if [ "$release_header" = "$NEW_VERSION" ] \
        && curl -sS -f "http://127.0.0.1:${APP_PORT}/health" > /dev/null 2>&1; then
        promoted=true
        break
    fi
    sleep 1
done

if [ "$promoted" != "true" ]; then
    echo "ERROR: ${NEW_PROJECT} failed its post-switch health check." >&2
    rollback_router
    $COMPOSE logs --tail 50 backend frontend
    exit 1
fi

if [ "$MODE" = "promote" ]; then
    if ! start_backup_service; then
        rollback_router
        exit 1
    fi
fi

if [ "$MODE" = "promote" ] || [ "$MODE" = "rollback" ]; then
    commit_deployment_state() {
        local promoted_at
        promoted_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        STATE_TMP="${STATE_FILE}.tmp.$$"
        VERSION_TMP="${VERSION_FILE}.tmp.$$"
        {
            printf 'format_version=1\n'
            printf 'current_version=%s\n' "$NEW_VERSION"
            printf 'previous_version=%s\n' "$OLD_VERSION"
            printf 'git_commit=%s\n' "$DEPLOY_GIT_COMMIT"
            printf 'previous_git_commit=%s\n' "$OLD_GIT_COMMIT"
            printf 'promoted_at=%s\n' "$promoted_at"
            printf 'status=promoted\n'
        } > "$STATE_TMP" || return 1
        printf '%s\n' "$NEW_VERSION" > "$VERSION_TMP" || return 1
        mv "$STATE_TMP" "$STATE_FILE" || return 1
        # The legacy version file remains the commit point for existing scripts.
        # It is replaced last, after the richer state is durable.
        mv "$VERSION_TMP" "$VERSION_FILE"
    }
    if ! commit_deployment_state; then
        echo "ERROR: could not commit deployment state; restoring the previous route." >&2
        rollback_router
        exit 1
    fi
else
    echo "Live route for cdss-${NEW_VERSION} repaired and verified."
fi
PROMOTION_COMPLETE=true

# Nginx's old workers retain established requests after reload. Wait for them
# to finish before allowing prune to remove the old backend/frontend. If a
# genuinely long request is still active, retain the old stacks and networks;
# a later deployment will prune them after the worker exits.
router_drained=false
for i in $(seq 1 30); do
    if ! router_processes="$(docker exec "$ROUTER_NAME" ps -o args 2>/dev/null)"; then
        echo "Could not inspect router workers; preserving old release resources." >&2
        break
    fi
    if ! printf '%s\n' "$router_processes" \
        | grep -q '[w]orker process is shutting down'; then
        router_drained=true
        break
    fi
    sleep 1
done

if [ "$router_drained" = "true" ]; then
    rm -f "$DRAIN_FILE"
    while IFS= read -r network; do
        if [ -n "$network" ] \
            && [ "$network" != "$NEW_NETWORK" ] \
            && [[ "$network" == cdss-* ]]; then
            docker network disconnect "$network" "$ROUTER_NAME" || true
        fi
    done < <(
        docker inspect \
            -f '{{range $name, $settings := .NetworkSettings.Networks}}{{println $name}}{{end}}' \
            "$ROUTER_NAME"
    )
else
    echo "Long-running requests are still draining; preserving old release resources."
    : > "$DRAIN_FILE"
fi

echo "${NEW_PROJECT} healthy and live through ${ROUTER_NAME} on port ${APP_PORT}."
