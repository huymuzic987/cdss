#!/usr/bin/env bash
# Repairs the public route to the last promoted release before a new build
# begins. This keeps a missing/stopped router from extending an outage through
# image builds, database cloning, migrations, and seeding.
set -euo pipefail

VERSION_FILE="deploy/.current_version"
CURRENT_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"

if [ -z "$CURRENT_VERSION" ]; then
    echo "No promoted release is recorded; live-route repair is not needed."
    exit 0
fi

echo "Ensuring public route to cdss-${CURRENT_VERSION}..."
exec bash deploy/promote_stack.sh "$CURRENT_VERSION" route-only
