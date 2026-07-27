#!/usr/bin/env bash
# Keeps at most KEEP_RETENTION stopped old stacks around (for manual
# rollback/debugging) and fully removes -- containers, volume, and images --
# anything older than that, so disk/memory usage doesn't grow with every
# deploy. The dedicated backup container is not needed in retained rollback
# stacks, so it is removed from every non-live stack. Run after a successful
# promote_stack.sh.
#
# "Old stacks" are discovered from container names (docker compose prefixes
# every container with its project name, e.g. cdss-42-db-1) rather than a
# hand-maintained list, so this can't drift out of sync with what's
# actually on the host.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

KEEP_RETENTION=2
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

# Only the live stack needs to run scheduled backups. Remove the stopped
# backup service container from retained rollback stacks while preserving
# their db, backend, frontend, database volume, and application images.
for v in "${old_versions[@]}"; do
    echo "Removing unnecessary backup container from old stack cdss-${v}..."
    if ! ( export VERSION="$v"; resolve_compose "cdss-${v}"; $COMPOSE rm -f -s backup ); then
        echo "WARNING: could not remove backup container from cdss-${v}; continuing prune." >&2
    fi
done

to_remove_count=$(( ${#old_versions[@]} - KEEP_RETENTION ))
if [ "$to_remove_count" -gt 0 ]; then
    for i in $(seq 0 $((to_remove_count - 1))); do
        v="${old_versions[$i]}"
        echo "Removing old stack cdss-${v} (containers, volume, images)..."
        ( export VERSION="$v"; resolve_compose "cdss-${v}"; $COMPOSE down -v --rmi all )
    done
else
    echo "Nothing to prune (${#old_versions[@]} old stack(s), keeping up to ${KEEP_RETENTION})."
fi

echo "Live version: cdss-${CURRENT_VERSION}."
