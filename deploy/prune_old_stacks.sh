#!/usr/bin/env bash
# Keeps at most KEEP_RETENTION stopped old database containers and volumes as
# rollback copies. Backend, release frontend, backup containers, and versioned
# app images are removed from every old stack to avoid wasting disk and memory.
# The dedicated stable cdss-router has no release Compose labels and is never
# selected by these project-scoped cleanup operations.
# Database stacks older than the retention window are removed completely.
#
# "Old stacks" are discovered from container names (docker compose prefixes
# every container with its project name, e.g. cdss-42-db-1) rather than a
# hand-maintained list, so this can't drift out of sync with what's
# actually on the host.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

KEEP_RETENTION=3
VERSION_FILE="deploy/.current_version"
DRAIN_FILE="deploy/.router_drain_pending"
CURRENT_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || echo "")"
ROUTER_ID="$(docker ps -aq --filter 'name=^/cdss-router$' | head -n 1)"

validate_dotenv_file .env
DOTENV_APP_PORT="$(dotenv_get .env APP_PORT || true)"
APP_PORT="${PUBLIC_APP_PORT:-${DOTENV_APP_PORT:-3000}}"

remove_project_service_containers() {
    local project="$1"
    local service="$2"
    local container_id=""

    while IFS= read -r container_id; do
        [ -z "$container_id" ] && continue
        if [ -n "$ROUTER_ID" ] && [ "$container_id" = "$ROUTER_ID" ]; then
            echo "Preserving ${container_id}: it is the stable cdss-router."
            continue
        fi
        docker rm -f "$container_id"
    done < <(
        docker ps -aq \
            --filter "label=com.docker.compose.project=${project}" \
            --filter "label=com.docker.compose.service=${service}"
    )
}

stop_project_service_containers() {
    local project="$1"
    local service="$2"
    local container_id=""

    while IFS= read -r container_id; do
        [ -z "$container_id" ] || docker stop "$container_id" > /dev/null
    done < <(
        docker ps -q \
            --filter "label=com.docker.compose.project=${project}" \
            --filter "label=com.docker.compose.service=${service}"
    )
}

if [ -f "$DRAIN_FILE" ]; then
    preserve_for_drain=false
    if [ -z "$ROUTER_ID" ] \
        || [ "$(docker inspect -f '{{.State.Running}}' "$ROUTER_ID")" != "true" ]; then
        preserve_for_drain=true
    elif ! router_processes="$(docker exec "$ROUTER_ID" ps -o args 2>/dev/null)"; then
        preserve_for_drain=true
    elif printf '%s\n' "$router_processes" \
        | grep -q '[w]orker process is shutting down'; then
        preserve_for_drain=true
    fi

    if [ "$preserve_for_drain" = "true" ]; then
        echo "Router requests are still draining; preserving old stacks for this run."
        exit 0
    fi
    rm -f "$DRAIN_FILE"
fi

mapfile -t all_versions < <(
    docker ps -a --format '{{.Names}}' \
        | grep -oE '^cdss-[0-9]+' \
        | sed 's/^cdss-//' \
        | sort -un
)

old_versions=()
for v in "${all_versions[@]}"; do
    if [ "$v" != "$CURRENT_VERSION" ]; then
        old_versions+=("$v")
    fi
done

# Only database containers and volumes are retained for old versions.
for v in "${old_versions[@]}"; do
    echo "Keeping database only for old stack cdss-${v}..."
    (
        project="cdss-${v}"
        remove_project_service_containers "$project" backend
        remove_project_service_containers "$project" backup
        remove_project_service_containers "$project" frontend
        stop_project_service_containers "$project" db
    ) || echo "WARNING: could not remove application containers from cdss-${v}; continuing prune." >&2

    docker image rm "cdss-backend:${v}" "cdss-frontend:${v}" > /dev/null 2>&1 || true
done

to_remove_count=$(( ${#old_versions[@]} - KEEP_RETENTION ))
if [ "$to_remove_count" -gt 0 ]; then
    for i in $(seq 0 $((to_remove_count - 1))); do
        v="${old_versions[$i]}"
        echo "Removing expired database stack cdss-${v} (container and volume)..."
        (
            project="cdss-${v}"
            remove_project_service_containers "$project" db

            # Remove only unused project resources by label.
            while IFS= read -r volume; do
                [ -z "$volume" ] || docker volume rm "$volume"
            done < <(
                docker volume ls -q \
                    --filter "label=com.docker.compose.project=${project}"
            )

            while IFS= read -r network; do
                [ -z "$network" ] || docker network rm "$network" > /dev/null 2>&1 || true
            done < <(
                docker network ls -q \
                    --filter "label=com.docker.compose.project=${project}"
            )
        )
    done
else
    echo "Nothing to prune (${#old_versions[@]} old stack(s), keeping up to ${KEEP_RETENTION})."
fi

if [ -z "$CURRENT_VERSION" ]; then
    echo "ERROR: no live version is recorded after pruning." >&2
    exit 1
fi
if [ -z "$ROUTER_ID" ] \
    || [ "$(docker inspect -f '{{.State.Running}}' "$ROUTER_ID" 2>/dev/null || true)" != "true" ]; then
    echo "ERROR: stable router is not running after pruning." >&2
    exit 1
fi

release_header="$(
    curl -sS -f -D - -o /dev/null "http://127.0.0.1:${APP_PORT}/" 2>/dev/null \
        | tr -d '\r' \
        | sed -n 's/^X-CDSS-Release: //p' \
        | tail -n 1 \
        || true
)"
if [ "$release_header" != "$CURRENT_VERSION" ] \
    || ! curl -sS -f "http://127.0.0.1:${APP_PORT}/health" > /dev/null 2>&1; then
    echo "ERROR: live route failed after pruning (expected release ${CURRENT_VERSION}, got ${release_header:-none})." >&2
    docker logs --tail 50 "$ROUTER_ID" >&2 || true
    exit 1
fi

echo "Live version: cdss-${CURRENT_VERSION}."
