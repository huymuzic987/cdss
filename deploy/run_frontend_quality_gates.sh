#!/usr/bin/env sh
# Runs inside the pinned Node container created by run_quality_gates.sh.
# Invoke each tool directly so failures retain the tool name, diagnostics, and
# exit code instead of ending with pnpm's generic ELIFECYCLE lifecycle message.
set -eu

PNPM_VERSION="${PNPM_VERSION:-9.15.9}"

run_gate() {
    gate_name="$1"
    shift
    echo "=== Frontend gate: ${gate_name} ==="
    if "$@"; then
        echo "PASS: ${gate_name}"
    else
        gate_status=$?
        echo "ERROR: ${gate_name} failed with exit code ${gate_status}." >&2
        exit "$gate_status"
    fi
}

corepack enable
corepack prepare "pnpm@${PNPM_VERSION}" --activate

node -e "
    if (typeof require('node:worker_threads').markAsUncloneable !== 'function') {
        throw new Error('Node runtime lacks worker_threads.markAsUncloneable')
    }
"

node --version
pnpm --version
pnpm config set store-dir /tmp/pnpm-store
pnpm install --frozen-lockfile

run_gate "Vitest unit/component tests" pnpm exec vitest run
run_gate "Oxlint" pnpm exec oxlint
run_gate "TypeScript compilation" pnpm exec tsc -b
run_gate "Vite production build" pnpm exec vite build
