#!/usr/bin/env sh
# Runs inside the pinned Node container created by run_quality_gates.sh.
# Invoke each tool directly so failures retain the tool name, diagnostics, and
# exit code instead of ending with pnpm's generic ELIFECYCLE lifecycle message.
set -eu

PNPM_VERSION="${PNPM_VERSION:-9.15.9}"
PNPM_STORE_DIR="${PNPM_STORE_DIR:-/tmp/pnpm-store}"
CDSS_TIMING_FILE="${CDSS_TIMING_FILE:-.ci-reports/timings.tsv}"

run_gate() {
    gate_name="$1"
    shift
    started_at="$(date +%s)"
    echo "=== Frontend gate: ${gate_name} ==="
    if "$@"; then
        elapsed=$(($(date +%s) - started_at))
        printf 'CDSS_TIMING\t%s\t%s\t0\n' "$gate_name" "$elapsed"
        printf '%s\t%s\t0\n' "$gate_name" "$elapsed" >> "$CDSS_TIMING_FILE" || true
        echo "PASS: ${gate_name}"
    else
        gate_status=$?
        elapsed=$(($(date +%s) - started_at))
        printf 'CDSS_TIMING\t%s\t%s\t%s\n' "$gate_name" "$elapsed" "$gate_status"
        printf '%s\t%s\t%s\n' "$gate_name" "$elapsed" "$gate_status" \
            >> "$CDSS_TIMING_FILE" || true
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
pnpm config set store-dir "$PNPM_STORE_DIR"

# node_modules is a persistent Docker volume. Avoid pnpm's expensive relink
# pass when the exact dependency inputs are already installed, while still
# forcing a frozen install after any manifest/lockfile change or interrupted
# install. The marker is written only after pnpm succeeds.
dependency_key="$(
    sha256sum package.json pnpm-lock.yaml \
        | sha256sum \
        | awk '{print $1}'
)"
dependency_marker="node_modules/.cdss-dependency-key"
installed_key="$(cat "$dependency_marker" 2>/dev/null || true)"
if [ "$installed_key" = "$dependency_key" ] \
    && [ -x node_modules/.bin/vitest ] \
    && [ -x node_modules/.bin/oxlint ] \
    && [ -x node_modules/.bin/tsc ] \
    && [ -x node_modules/.bin/vite ]; then
    echo "Frontend dependency cache is current; skipping pnpm install."
else
    pnpm install --frozen-lockfile
    printf '%s\n' "$dependency_key" > "$dependency_marker"
fi

mkdir -p .ci-reports
run_gate "Vitest unit/component tests" \
    pnpm exec vitest run \
        --reporter=default \
        --reporter=junit \
        --outputFile.junit=./.ci-reports/junit.xml
run_gate "Oxlint" pnpm exec oxlint
run_gate "TypeScript compilation" pnpm exec tsc -b
run_gate "Vite production build" pnpm exec vite build
