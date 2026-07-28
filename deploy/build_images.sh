#!/usr/bin/env bash
# Builds each application image exactly once for this deployment. Compose
# builds backend and frontend concurrently and reuses the host's BuildKit
# layer cache, minimizing elapsed build time.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

VERSION="${1:?usage: build_images.sh <version>}"
export VERSION
resolve_compose "cdss-${VERSION}"

set -a
source .env
set +a

echo "Building backend and frontend images for cdss-${VERSION} in parallel..."
COMPOSE_PARALLEL_LIMIT=-1 DOCKER_BUILDKIT=1 $COMPOSE build backend frontend
