#!/usr/bin/env bash
# Shared helper for deploy/*.sh scripts. Figures out which Docker Compose
# CLI is available on this host and sets $COMPOSE accordingly - not every
# host has the newer `docker compose` plugin; some only have the legacy
# standalone docker-compose binary.
#
# Pass a compose project name (e.g. "cdss-42") to get an isolated stack --
# its own containers, network, and volume -- side by side with any other
# project. Omit it for the default (unnamed) project, e.g. for one-off local
# use. See provision_stack.sh/promote_stack.sh/prune_old_stacks.sh for how
# the blue/green deploy flow uses this.
resolve_compose() {
    local project="${1:-}"
    local project_flag=""
    if [ -n "$project" ]; then
        project_flag="-p $project"
    fi
    if docker compose version > /dev/null 2>&1; then
        COMPOSE="docker compose $project_flag -f docker-compose.prod.yml"
    elif command -v docker-compose > /dev/null 2>&1; then
        COMPOSE="docker-compose $project_flag -f docker-compose.prod.yml"
    else
        echo "ERROR: neither the docker compose plugin nor the standalone docker-compose is installed on this host" >&2
        exit 1
    fi
}

# Log a stable, tab-separated duration record while preserving the wrapped
# command's exit status. Jenkins can collect CDSS_TIMING lines without making
# reporting a dependency of deployment correctness.
run_timed() {
    local operation_name="$1"
    shift
    local started_at finished_at elapsed status
    started_at="$(date +%s)"
    echo "=== Timing start: ${operation_name} ==="
    if "$@"; then
        status=0
    else
        status=$?
    fi
    finished_at="$(date +%s)"
    elapsed=$((finished_at - started_at))
    printf 'CDSS_TIMING\t%s\t%s\t%s\n' "$operation_name" "$elapsed" "$status"
    return "$status"
}

# Validate the dotenv subset used by Docker Compose without executing it as
# shell code. Duplicate keys and malformed quoting fail closed.
validate_dotenv_file() {
    local env_file="${1:?validate_dotenv_file <file>}"
    local line line_number=0 key value first last
    declare -A seen_keys=()

    if [ ! -f "$env_file" ]; then
        echo "ERROR: environment file does not exist: $env_file" >&2
        return 1
    fi

    while IFS= read -r line || [ -n "$line" ]; do
        line_number=$((line_number + 1))
        line="${line%$'\r'}"
        [ -z "$line" ] && continue
        [[ "$line" == \#* ]] && continue
        if [[ ! "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            echo "ERROR: malformed dotenv entry at ${env_file}:${line_number}." >&2
            return 1
        fi
        key="${line%%=*}"
        value="${line#*=}"
        if [ -n "${seen_keys[$key]+present}" ]; then
            echo "ERROR: duplicate dotenv key '$key' in $env_file." >&2
            return 1
        fi
        seen_keys["$key"]=1
        if [ -n "$value" ]; then
            first="${value:0:1}"
            last="${value: -1}"
            if { [ "$first" = "'" ] || [ "$first" = '"' ]; } \
                && [ "$last" != "$first" ]; then
                echo "ERROR: unterminated quoted value for '$key' in $env_file." >&2
                return 1
            fi
        fi
    done < "$env_file"
}

dotenv_get() {
    local env_file="${1:?dotenv_get <file> <key>}"
    local requested_key="${2:?dotenv_get <file> <key>}"
    local line value first last

    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%$'\r'}"
        [[ "$line" == "$requested_key="* ]] || continue
        value="${line#*=}"
        if [ -n "$value" ]; then
            first="${value:0:1}"
            last="${value: -1}"
            if { [ "$first" = "'" ] || [ "$first" = '"' ]; } \
                && [ "$last" = "$first" ]; then
                value="${value:1:${#value}-2}"
            fi
        fi
        printf '%s' "$value"
        return 0
    done < "$env_file"
    return 1
}

dotenv_require() {
    local env_file="$1"
    local requested_key="$2"
    local value
    if ! value="$(dotenv_get "$env_file" "$requested_key")" || [ -z "$value" ]; then
        echo "ERROR: required dotenv key '$requested_key' is missing or empty in $env_file." >&2
        return 1
    fi
    printf '%s' "$value"
}
