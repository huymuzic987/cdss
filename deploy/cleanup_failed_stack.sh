#!/usr/bin/env bash
# Removes a failed candidate stack unless that version was already promoted.
# Keeping this logic on the target host avoids fragile nested quoting and
# command substitution inside the Jenkins SSH command.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

FAILED_VERSION="${1:?usage: cleanup_failed_stack.sh <version>}"
VERSION_FILE="deploy/.current_version"
CURRENT_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"

if [ "$CURRENT_VERSION" = "$FAILED_VERSION" ]; then
    echo "Version ${FAILED_VERSION} is already live; leaving it running."
    exit 0
fi

export VERSION="$FAILED_VERSION"
resolve_compose "cdss-${FAILED_VERSION}"

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "Removing failed candidate stack cdss-${FAILED_VERSION}..."
if ! $COMPOSE down -v; then
    echo "WARNING: failed candidate cleanup did not complete." >&2
fi
docker image rm \
    "cdss-backend:${FAILED_VERSION}" \
    "cdss-frontend:${FAILED_VERSION}" > /dev/null 2>&1 || true

# Cleanup is a best-effort post action. The original pipeline stage remains
# the authoritative failure and the live router must not be affected.
exit 0
