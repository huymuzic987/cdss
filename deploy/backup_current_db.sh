#!/usr/bin/env bash
# Creates a deployment-time backup of the currently-live database before a
# new stack is provisioned. The dedicated backup service image connects to
# the old stack's db over its existing Compose network.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

VERSION_FILE="deploy/.current_version"
OLD_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"

if [ -z "$OLD_VERSION" ]; then
    echo "No current deployment version is recorded; skipping pre-deployment backup."
    exit 0
fi

set -a
source .env
set +a

export VERSION="$OLD_VERSION"
export BACKUP_HOST_DIR="${BACKUP_HOST_DIR:-./persistent-backups}"

mkdir -p "$BACKUP_HOST_DIR"
chmod 0755 "$BACKUP_HOST_DIR"

resolve_compose "cdss-${OLD_VERSION}"

DB_CONTAINER="$($COMPOSE ps -q db)"
if [ -z "$DB_CONTAINER" ] || [ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER")" != "true" ]; then
    echo "ERROR: database container for cdss-${OLD_VERSION} is not running" >&2
    exit 1
fi

# .env already contains the incoming deployment's configuration at this
# point. Read credentials from the old db container itself so a credential
# rotation cannot prevent its final backup.
container_env() {
    local key="$1"
    docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$DB_CONTAINER" \
        | sed -n "s/^${key}=//p" \
        | head -n 1
}

export POSTGRES_USER="$(container_env POSTGRES_USER)"
export POSTGRES_PASSWORD="$(container_env POSTGRES_PASSWORD)"
export POSTGRES_DB="$(container_env POSTGRES_DB)"

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo "ERROR: could not read database credentials from cdss-${OLD_VERSION}" >&2
    exit 1
fi

echo "Backing up currently-live database from cdss-${OLD_VERSION}..."
$COMPOSE run --rm --no-deps backup backup-now
