#!/usr/bin/env bash
# Builds and starts the backend + frontend containers.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
resolve_compose

$COMPOSE up -d --build backend frontend
