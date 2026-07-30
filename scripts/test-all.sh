#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== Backend ==="
./scripts/test-backend.sh

echo
echo "=== Frontend ==="
./frontend/test-frontend.sh
