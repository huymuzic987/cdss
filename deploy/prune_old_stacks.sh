#!/usr/bin/env bash
# Keeps at most KEEP_RETENTION stopped old database containers and volumes as
# rollback copies. Backend, release frontend, backup containers, and versioned
# app images are removed from every old stack to avoid wasting disk and memory.
# The stable cdss-router may carry Compose labels from the frontend container
# that was adopted during zero-downtime bootstrap; it is never removed here.
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
        export VERSION="$v"
        resolve_compose "cdss-${v}"
        $COMPOSE rm -f -s backend backup

        frontend_id="$($COMPOSE ps -q frontend)"
        if [ -n "$frontend_id" ] && [ "$frontend_id" = "$ROUTER_ID" ]; then
            echo "Preserving ${frontend_id}: it is the stable cdss-router."
        else
            $COMPOSE rm -f -s frontend
        fi
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
            export VERSION="$v"
            resolve_compose "$project"
            $COMPOSE rm -f -s db

            # Do not use `compose down`: an adopted router retains its original
            # Compose labels, and `down` would stop it even after it has been
            # renamed. Remove only unused project resources by label.
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

echo "Live version: cdss-${CURRENT_VERSION}."
