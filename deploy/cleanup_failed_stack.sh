#!/usr/bin/env bash
# Removes a failed candidate stack unless that version was already promoted.
# Keeping this logic on the target host avoids fragile nested quoting and
# command substitution inside the Jenkins SSH command.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

FAILED_VERSION="${1:?usage: cleanup_failed_stack.sh <version>}"
VERSION_FILE="deploy/state/.current_version"
STATE_FILE="deploy/state/.deployment_state"
WRITE_LOCK_FILE="deploy/state/.write_lock"
CURRENT_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"

if [ "$CURRENT_VERSION" = "$FAILED_VERSION" ]; then
    state_value() {
        local key="$1"
        sed -n "s/^${key}=//p" "$STATE_FILE" 2>/dev/null | head -n 1 || true
    }

    PREVIOUS_VERSION="$(state_value previous_version)"
    PREVIOUS_GIT_COMMIT="$(state_value previous_git_commit)"
    STATE_CURRENT_VERSION="$(state_value current_version)"

    # The write lock proves no application writes have entered the promoted
    # database yet. Only in that state is automatic database rollback safe.
    if [ -f "$WRITE_LOCK_FILE" ] \
        && [ "$STATE_CURRENT_VERSION" = "$FAILED_VERSION" ] \
        && [ -n "$PREVIOUS_VERSION" ] \
        && [ "$PREVIOUS_VERSION" != "$FAILED_VERSION" ]; then
        echo "Promoted release ${FAILED_VERSION} failed before writes resumed."
        echo "Rolling the stable route and current-version state back to cdss-${PREVIOUS_VERSION}..."
        if ! DEPLOY_GIT_COMMIT="${PREVIOUS_GIT_COMMIT:-unknown}" \
            bash deploy/promote_stack.sh "$PREVIOUS_VERSION" rollback; then
            echo "ERROR: previous release could not be restored; preserving the write lock and both stacks." >&2
            exit 1
        fi
        CURRENT_VERSION="$PREVIOUS_VERSION"
    else
        echo "Version ${FAILED_VERSION} was promoted before the later pipeline failure."
        echo "Automatic rollback is unsafe after writes resume or without a previous release."
        echo "Repairing and verifying the promoted route before leaving it running..."
        if ! bash deploy/promote_stack.sh "$CURRENT_VERSION" route-only; then
            echo "ERROR: promoted release route could not be repaired; preserving its containers for diagnosis." >&2
            exit 1
        fi
        exit 0
    fi
fi

export VERSION="$FAILED_VERSION"
PROJECT="cdss-${FAILED_VERSION}"
ROUTER_ID="$(docker ps -aq --filter 'name=^/cdss-router$' | head -n 1)"

# Restore the last committed live release before removing a candidate that may
# have been loaded into nginx immediately before an interrupted promotion.
if [ -n "$CURRENT_VERSION" ]; then
    echo "Restoring and verifying public route to cdss-${CURRENT_VERSION}..."
    if ! bash deploy/promote_stack.sh "$CURRENT_VERSION" route-only; then
        echo "WARNING: could not restore the last promoted route." >&2
        echo "Preserving failed candidate ${PROJECT} to avoid removing a possible active upstream." >&2
        exit 0
    fi
elif [ -n "$ROUTER_ID" ]; then
    echo "No promoted release exists; removing the unusable first-deploy router."
    docker rm -f "$ROUTER_ID" > /dev/null 2>&1 || true
    ROUTER_ID=""
fi

echo "Removing failed candidate stack ${PROJECT}..."

while IFS= read -r container_id; do
    [ -z "$container_id" ] && continue
    if [ -n "$ROUTER_ID" ] && [ "$container_id" = "$ROUTER_ID" ]; then
        echo "Preserving ${container_id}: it is the stable cdss-router."
        continue
    fi
    docker rm -f "$container_id" || true
done < <(
    docker ps -aq --filter "label=com.docker.compose.project=${PROJECT}"
)

# A failed promotion may have connected the stable router before interruption.
# Disconnect it before deleting candidate networks.
if [ -n "$ROUTER_ID" ]; then
    while IFS= read -r network; do
        [ -z "$network" ] && continue
        docker network disconnect "$network" "$ROUTER_ID" > /dev/null 2>&1 || true
    done < <(
        docker network ls -q --filter "label=com.docker.compose.project=${PROJECT}"
    )
fi

while IFS= read -r network; do
    [ -z "$network" ] || docker network rm "$network" > /dev/null 2>&1 || true
done < <(
    docker network ls -q --filter "label=com.docker.compose.project=${PROJECT}"
)

while IFS= read -r volume; do
    [ -z "$volume" ] || docker volume rm "$volume" > /dev/null 2>&1 || true
done < <(
    docker volume ls -q --filter "label=com.docker.compose.project=${PROJECT}"
)

docker image rm \
    "cdss-backend:${FAILED_VERSION}" \
    "cdss-frontend:${FAILED_VERSION}" > /dev/null 2>&1 || true

remaining="$(
    docker ps -aq --filter "label=com.docker.compose.project=${PROJECT}" \
        | grep -v -F "${ROUTER_ID:-__no_router__}" \
        || true
)"
if [ -n "$remaining" ]; then
    echo "WARNING: candidate containers remain after cleanup: ${remaining}" >&2
fi

# Cleanup is a best-effort post action. The original pipeline stage remains
# the authoritative failure and the live router must not be affected.
exit 0
