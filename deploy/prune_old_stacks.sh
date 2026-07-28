#!/usr/bin/env bash
# Keeps at most KEEP_RETENTION stopped old database containers and volumes as
# rollback copies. Backend, frontend, backup containers, and versioned app
# images are removed from every old stack to avoid wasting disk and memory.
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
CURRENT_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || echo "")"

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
    if ! ( export VERSION="$v"; resolve_compose "cdss-${v}"; $COMPOSE rm -f -s backend frontend backup ); then
        echo "WARNING: could not remove application containers from cdss-${v}; continuing prune." >&2
    fi
    docker image rm "cdss-backend:${v}" "cdss-frontend:${v}" > /dev/null 2>&1 || true
done

to_remove_count=$(( ${#old_versions[@]} - KEEP_RETENTION ))
if [ "$to_remove_count" -gt 0 ]; then
    for i in $(seq 0 $((to_remove_count - 1))); do
        v="${old_versions[$i]}"
        echo "Removing expired database stack cdss-${v} (container and volume)..."
        ( export VERSION="$v"; resolve_compose "cdss-${v}"; $COMPOSE down -v )
    done
else
    echo "Nothing to prune (${#old_versions[@]} old stack(s), keeping up to ${KEEP_RETENTION})."
fi

echo "Live version: cdss-${CURRENT_VERSION}."
