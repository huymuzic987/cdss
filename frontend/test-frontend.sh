#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Typecheck (tsc --noEmit)"
pnpm exec tsc --noEmit

echo
echo "==> Lint (oxlint)"
pnpm run lint

echo
echo "==> Tests (vitest run)"
pnpm vitest run
