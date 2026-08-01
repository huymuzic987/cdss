#!/usr/bin/env bash
# Removes source checkouts only after their Compose projects have disappeared.
# Persistent environment, deployment state, and backups live outside this tree.
set -euo pipefail

RELEASES_DIR="${CDSS_RELEASES_DIR:-}"
VERSION_FILE="deploy/state/.current_version"
CURRENT_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"

if [ -z "$RELEASES_DIR" ]; then
    echo "ERROR: CDSS_RELEASES_DIR is required." >&2
    exit 1
fi
case "$RELEASES_DIR" in
    /*/releases) ;;
    *)
        echo "ERROR: refusing to prune unsafe releases path: $RELEASES_DIR" >&2
        exit 1
        ;;
esac
if [ ! -d "$RELEASES_DIR" ]; then
    echo "ERROR: releases directory does not exist: $RELEASES_DIR" >&2
    exit 1
fi

declare -A retained=()
if [[ "$CURRENT_VERSION" =~ ^[0-9]+$ ]]; then
    retained["$CURRENT_VERSION"]=1
fi
while IFS= read -r version; do
    [ -z "$version" ] || retained["$version"]=1
done < <(
    docker ps -a --format '{{.Names}}' \
        | grep -oE '^cdss-[0-9]+' \
        | sed 's/^cdss-//' \
        | sort -u \
        || true
)

removed=0
for release_dir in "$RELEASES_DIR"/[0-9]*; do
    [ -d "$release_dir" ] || continue
    version="${release_dir##*/}"
    [[ "$version" =~ ^[0-9]+$ ]] || continue
    if [ -n "${retained[$version]+keep}" ]; then
        echo "Retaining release source $version."
        continue
    fi
    echo "Removing orphaned release source $release_dir."
    rm -rf -- "$release_dir"
    removed=$((removed + 1))
done

echo "Removed $removed orphaned release source directorie(s)."
