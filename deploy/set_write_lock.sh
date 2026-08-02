#!/usr/bin/env bash
# Enables or disables the deployment write barrier on the stable router.
# The marker is host-persistent and promote_stack.sh preserves it while routing
# changes, so writes remain blocked through candidate and public verification.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

MODE="${1:?usage: set_write_lock.sh <enable|disable|status>}"
VERSION_FILE="deploy/state/.current_version"
WRITE_LOCK_FILE="deploy/state/.write_lock"
DRAIN_FILE="deploy/state/.router_drain_pending"
PROBE_PATH="/__deployment/write-lock-probe"
PROBE_ATTEMPTS="${WRITE_LOCK_PROBE_ATTEMPTS:-10}"
PROBE_RETRY_DELAY="${WRITE_LOCK_PROBE_RETRY_DELAY:-1}"

case "$MODE" in
    enable|disable|status) ;;
    *)
        echo "ERROR: mode must be enable, disable, or status." >&2
        exit 2
        ;;
esac

validate_dotenv_file .env
DOTENV_APP_PORT="$(dotenv_get .env APP_PORT || true)"
APP_PORT="${PUBLIC_APP_PORT:-${DOTENV_APP_PORT:-3000}}"

current_version() {
    cat "$VERSION_FILE" 2>/dev/null || true
}

probe_status() {
    curl --noproxy '*' -sS --max-time 10 \
        -o /dev/null \
        -w '%{http_code}' \
        -X POST \
        "http://127.0.0.1:${APP_PORT}${PROBE_PATH}" \
        2>/dev/null || true
}

wait_for_probe_status() {
    local expected_status="$1"
    local comparison="${2:-equal}"
    local attempt http_status

    for attempt in $(seq 1 "$PROBE_ATTEMPTS"); do
        http_status="$(probe_status)"
        echo "Write-lock probe attempt ${attempt}/${PROBE_ATTEMPTS}: HTTP ${http_status:-unreachable}" >&2

        if [ "$comparison" = "equal" ] && [ "$http_status" = "$expected_status" ]; then
            return 0
        fi
        if [ "$comparison" = "not-equal" ] \
            && [ -n "$http_status" ] \
            && [ "$http_status" != "$expected_status" ]; then
            return 0
        fi
        if [ "$attempt" -lt "$PROBE_ATTEMPTS" ]; then
            sleep "$PROBE_RETRY_DELAY"
        fi
    done
    return 1
}

reload_current_route() {
    local version
    version="$(current_version)"
    if [ -z "$version" ]; then
        echo "No promoted release exists; the marker will apply at first promotion."
        return 0
    fi
    PUBLIC_APP_PORT="$APP_PORT" bash deploy/promote_stack.sh "$version" route-only
}

restore_marker() {
    local was_enabled="$1"
    if [ "$was_enabled" = "true" ]; then
        : > "$WRITE_LOCK_FILE"
    else
        rm -f "$WRITE_LOCK_FILE"
    fi
}

if [ "$MODE" = "status" ]; then
    marker_enabled=false
    [ ! -f "$WRITE_LOCK_FILE" ] || marker_enabled=true
    http_status="$(probe_status)"
    echo "Write-lock marker: ${marker_enabled}"
    echo "Write-lock probe HTTP status: ${http_status:-unreachable}"
    if [ "$marker_enabled" = "true" ] && [ "$http_status" != "503" ]; then
        exit 1
    fi
    if [ "$marker_enabled" = "false" ] && [ "$http_status" = "503" ]; then
        exit 1
    fi
    exit 0
fi

previously_enabled=false
[ ! -f "$WRITE_LOCK_FILE" ] || previously_enabled=true

if [ "$MODE" = "enable" ]; then
    : > "$WRITE_LOCK_FILE"
else
    rm -f "$WRITE_LOCK_FILE"
fi

if ! reload_current_route; then
    echo "ERROR: router reload failed; restoring the previous write-lock state." >&2
    restore_marker "$previously_enabled"
    reload_current_route || echo "WARNING: unable to restore the previous router configuration." >&2
    exit 1
fi

if [ "$MODE" = "enable" ]; then
    if [ -f "$DRAIN_FILE" ]; then
        echo "ERROR: old router workers did not drain; refusing to begin the database clone." >&2
        restore_marker "$previously_enabled"
        reload_current_route || echo "WARNING: unable to restore the previous router configuration." >&2
        exit 1
    fi
    if [ -n "$(current_version)" ] && ! wait_for_probe_status 503; then
        echo "ERROR: write-lock probe did not return HTTP 503 after ${PROBE_ATTEMPTS} attempts." >&2
        restore_marker "$previously_enabled"
        reload_current_route || echo "WARNING: unable to restore the previous router configuration." >&2
        exit 1
    fi
    echo "Deployment write lock enabled and old router workers drained."
else
    if [ -n "$(current_version)" ] \
        && ! wait_for_probe_status 503 not-equal; then
        echo "ERROR: write-lock probe remained blocked or unreachable after ${PROBE_ATTEMPTS} attempts." >&2
        restore_marker "$previously_enabled"
        reload_current_route || echo "WARNING: unable to restore the previous router configuration." >&2
        exit 1
    fi
    echo "Deployment write lock disabled."
fi
