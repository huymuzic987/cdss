#!/usr/bin/env bash
# Builds only application images whose build inputs changed. Unchanged images
# are retagged from the last successful build without invoking a builder.
# When both images changed, Compose schedules both builds together so their
# independent dependency and compilation stages can use otherwise-idle CPU and
# I/O.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

VERSION="${1:?usage: build_images.sh <version>}"
export VERSION
resolve_compose "cdss-${VERSION}"
STATE_FILE="deploy/state/.build_state"
MIN_DOCKER_FREE_GB="${MIN_DOCKER_FREE_GB:-10}"
MIN_BUILD_MEMORY_MB="${MIN_BUILD_MEMORY_MB:-2048}"

validate_dotenv_file .env
VITE_TLDRAW_LICENSE_KEY="$(dotenv_get .env VITE_TLDRAW_LICENSE_KEY || true)"
PRODUCTION="$(dotenv_get .env PRODUCTION || true)"
PRODUCTION="${PRODUCTION:-1}"

require_positive_integer() {
    local name="$1"
    local value="$2"
    case "$value" in
        *[!0-9]*|'')
            echo "ERROR: ${name} must be a positive integer." >&2
            exit 1
            ;;
    esac
    if [ "$value" -lt 1 ]; then
        echo "ERROR: ${name} must be at least 1." >&2
        exit 1
    fi
}

check_build_capacity() {
    local docker_root available_kb required_kb memory_mb cpu_count
    require_positive_integer MIN_DOCKER_FREE_GB "$MIN_DOCKER_FREE_GB"
    require_positive_integer MIN_BUILD_MEMORY_MB "$MIN_BUILD_MEMORY_MB"

    docker_root="$(docker info --format '{{.DockerRootDir}}')"
    available_kb="$(df -Pk "$docker_root" | awk 'NR == 2 {print $4}')"
    required_kb=$((MIN_DOCKER_FREE_GB * 1024 * 1024))
    memory_mb="$(awk '/^MemAvailable:/ {print int($2 / 1024)}' /proc/meminfo)"
    cpu_count="$(nproc)"

    if [ -z "$available_kb" ] || [ "$available_kb" -lt "$required_kb" ]; then
        echo "ERROR: Docker storage needs at least ${MIN_DOCKER_FREE_GB} GiB free under $docker_root." >&2
        docker system df >&2 || true
        exit 1
    fi
    if [ -z "$memory_mb" ] || [ "$memory_mb" -lt "$MIN_BUILD_MEMORY_MB" ]; then
        echo "ERROR: image builds need at least ${MIN_BUILD_MEMORY_MB} MiB available memory." >&2
        exit 1
    fi

    BUILD_PARALLEL_LIMIT=1
    if [ "$memory_mb" -ge 4096 ] && [ "$cpu_count" -ge 2 ]; then
        BUILD_PARALLEL_LIMIT=2
    fi
    export BUILD_PARALLEL_LIMIT
    printf 'CDSS_BUILD_CAPACITY\tdocker_free_gib=%s\tmemory_mib=%s\tcpus=%s\tparallel=%s\n' \
        "$((available_kb / 1024 / 1024))" "$memory_mb" "$cpu_count" "$BUILD_PARALLEL_LIMIT"
    docker system df
}

hash_files() {
    # Include relative filenames as well as contents so renames are detected.
    while IFS= read -r -d '' file; do
        printf '%s\0' "$file"
        sha256sum "$file"
    done | sha256sum | awk '{print $1}'
}

backend_hash="$(
    find Dockerfile.backend pyproject.toml uv.lock README.md alembic.ini \
         src alembic data -type f -print0 \
        | sort -z \
        | hash_files
)"

frontend_hash="$(
    {
        find frontend -type f \
            -not -path 'frontend/node_modules/*' \
            -not -path 'frontend/dist/*' \
            -not -path 'frontend/.git/*' \
            -print0 \
            | sort -z \
            | hash_files
        printf '%s\0%s' \
            "${VITE_TLDRAW_LICENSE_KEY:-}" \
            "${PRODUCTION:-1}" \
            | sha256sum \
            | awk '{print $1}'
    } | sha256sum | awk '{print $1}'
)"

previous_version=""
previous_backend_hash=""
previous_frontend_hash=""
if [ -f "$STATE_FILE" ]; then
    # The state file is generated below and contains only numeric/hash values.
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    previous_version="${BUILD_STATE_VERSION:-}"
    previous_backend_hash="${BUILD_STATE_BACKEND_HASH:-}"
    previous_frontend_hash="${BUILD_STATE_FRONTEND_HASH:-}"
fi

image_exists() {
    docker image inspect "$1" > /dev/null 2>&1
}

backend_needs_build=true
frontend_needs_build=true

if [ -n "$previous_version" ] \
    && [ "$backend_hash" = "$previous_backend_hash" ] \
    && image_exists "cdss-backend:${previous_version}"; then
    echo "Backend inputs unchanged; reusing cdss-backend:${previous_version}."
    docker image tag "cdss-backend:${previous_version}" "cdss-backend:${VERSION}"
    backend_needs_build=false
fi

if [ -n "$previous_version" ] \
    && [ "$frontend_hash" = "$previous_frontend_hash" ] \
    && image_exists "cdss-frontend:${previous_version}"; then
    echo "Frontend inputs unchanged; reusing cdss-frontend:${previous_version}."
    docker image tag "cdss-frontend:${previous_version}" "cdss-frontend:${VERSION}"
    frontend_needs_build=false
fi

if [ "$backend_needs_build" = "true" ] || [ "$frontend_needs_build" = "true" ]; then
    check_build_capacity
fi

if [ "$backend_needs_build" = "true" ] \
    && [ "$frontend_needs_build" = "true" ]; then
    echo "Backend and frontend inputs changed; building with parallel limit ${BUILD_PARALLEL_LIMIT}..."
    if $COMPOSE build --help 2>&1 | grep -q -- '--parallel'; then
        COMPOSE_PARALLEL_LIMIT="$BUILD_PARALLEL_LIMIT" DOCKER_BUILDKIT=1 BUILDKIT_PROGRESS=plain run_timed \
            "application-images-build" \
            $COMPOSE build --parallel backend frontend
    else
        # Compose v2 schedules multiple requested services concurrently and
        # uses COMPOSE_PARALLEL_LIMIT as its worker cap.
        COMPOSE_PARALLEL_LIMIT="$BUILD_PARALLEL_LIMIT" DOCKER_BUILDKIT=1 BUILDKIT_PROGRESS=plain run_timed \
            "application-images-build" \
            $COMPOSE build backend frontend
    fi
else
    if [ "$backend_needs_build" = "true" ]; then
        echo "Backend inputs changed; building cdss-backend:${VERSION}..."
        COMPOSE_PARALLEL_LIMIT=1 DOCKER_BUILDKIT=1 BUILDKIT_PROGRESS=plain run_timed \
            "backend-image-build" $COMPOSE build backend
    fi

    if [ "$frontend_needs_build" = "true" ]; then
        echo "Frontend inputs changed; building cdss-frontend:${VERSION}..."
        COMPOSE_PARALLEL_LIMIT=1 DOCKER_BUILDKIT=1 BUILDKIT_PROGRESS=plain run_timed \
            "frontend-image-build" $COMPOSE build frontend
    fi
fi

temporary_state="${STATE_FILE}.tmp.$$"
{
    printf 'BUILD_STATE_VERSION=%q\n' "$VERSION"
    printf 'BUILD_STATE_BACKEND_HASH=%q\n' "$backend_hash"
    printf 'BUILD_STATE_FRONTEND_HASH=%q\n' "$frontend_hash"
} > "$temporary_state"
mv "$temporary_state" "$STATE_FILE"

echo "Application images are ready for cdss-${VERSION}."
