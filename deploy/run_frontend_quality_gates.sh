#!/usr/bin/env sh
# Runs inside the pinned Node container created by run_quality_gates.sh.
# Invoke each tool directly so failures retain the tool name, diagnostics, and
# exit code instead of ending with pnpm's generic ELIFECYCLE lifecycle message.
set -eu

PNPM_VERSION="${PNPM_VERSION:-9.15.9}"
PNPM_STORE_DIR="${PNPM_STORE_DIR:-/tmp/pnpm-store}"
CDSS_TIMING_FILE="${CDSS_TIMING_FILE:-.ci-reports/timings.tsv}"
CI_LOG_TAIL_LINES="${CI_LOG_TAIL_LINES:-80}"

run_gate() {
    gate_name="$1"
    log_file="$2"
    shift 2
    started_at="$(date +%s)"
    if "$@" >"$log_file" 2>&1; then
        elapsed=$(($(date +%s) - started_at))
        printf 'CDSS_TIMING\t%s\t%s\t0\n' "$gate_name" "$elapsed"
        printf '%s\t%s\t0\n' "$gate_name" "$elapsed" >> "$CDSS_TIMING_FILE" || true
        echo "PASS: ${gate_name} (${elapsed}s)"
    else
        gate_status=$?
        elapsed=$(($(date +%s) - started_at))
        printf 'CDSS_TIMING\t%s\t%s\t%s\n' "$gate_name" "$elapsed" "$gate_status"
        printf '%s\t%s\t%s\n' "$gate_name" "$elapsed" "$gate_status" \
            >> "$CDSS_TIMING_FILE" || true
        echo "ERROR: ${gate_name} failed with exit code ${gate_status}." >&2
        echo "--- ${log_file} (last ${CI_LOG_TAIL_LINES} lines) ---" >&2
        tail -n "$CI_LOG_TAIL_LINES" "$log_file" >&2 || true
        exit "$gate_status"
    fi
}

mkdir -p .ci-reports
corepack enable >.ci-reports/tooling.log 2>&1
corepack prepare "pnpm@${PNPM_VERSION}" --activate >>.ci-reports/tooling.log 2>&1

node -e "
    if (typeof require('node:worker_threads').markAsUncloneable !== 'function') {
        throw new Error('Node runtime lacks worker_threads.markAsUncloneable')
    }
"

echo "Node $(node --version); pnpm $(pnpm --version)"
pnpm config set store-dir "$PNPM_STORE_DIR"
if pnpm install --frozen-lockfile >.ci-reports/pnpm-install.log 2>&1; then
    echo "PASS: frontend dependency install"
else
    install_status=$?
    echo "ERROR: frontend dependency install failed with exit code ${install_status}." >&2
    echo "--- .ci-reports/pnpm-install.log (last ${CI_LOG_TAIL_LINES} lines) ---" >&2
    tail -n "$CI_LOG_TAIL_LINES" .ci-reports/pnpm-install.log >&2 || true
    exit "$install_status"
fi

run_gate "Vitest unit/component tests" \
    .ci-reports/vitest.log \
    pnpm exec vitest run \
        --reporter=dot \
        --reporter=junit \
        --outputFile.junit=./.ci-reports/junit.xml
run_gate "Oxlint" .ci-reports/oxlint.log pnpm exec oxlint
run_gate "TypeScript compilation" .ci-reports/typescript.log pnpm exec tsc -b
run_gate "Vite production build" .ci-reports/vite-build.log pnpm exec vite build
