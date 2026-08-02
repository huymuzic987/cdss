# CI/CD Performance Improvement Design

## Context

The deployment pipeline is functionally healthy and currently preserves the
full validation and deployment safety sequence. Its critical path is still
longer than desired because the frontend reinstalls dependencies into a fresh
workspace, backend static analysis waits for the test suite, and candidate
PostgreSQL readiness is checked at a coarse interval.

The goal is to make successful builds consistently approach and remain below
two minutes while retaining every existing validation gate and the current
low-memory deployment safeguards. The change is intentionally conservative:
it does not introduce a registry, artifact promotion, selective tests, or a
new deployment architecture.

## Goals

- Retain all backend and frontend quality gates on every normal build.
- Reduce the quality-gate critical path through safe dependency reuse and
  bounded backend concurrency.
- Reduce avoidable candidate-startup delay without weakening readiness checks.
- Preserve machine-readable timing, JUnit, and coverage evidence.
- Reduce repeated dependency work and avoid unnecessary resource consumption.
- Measure the complete Jenkins pipeline repeatedly before claiming the
  two-minute target.

## Non-goals

- Skipping or selecting a subset of tests, linters, type checks, or builds.
- Replacing the frontend quality-gate build with a previously generated
  artifact.
- Publishing application images to a remote registry.
- Increasing Docker build concurrency on the current approximately 3.5 GiB
  deployment host.
- Turning normal runtime variability into a hard Jenkins performance failure.

## Design

### Frontend dependency reuse

Add a persistent named volume for `frontend/node_modules` next to the existing
pnpm store volume. Mount it at the frontend quality-gate container's
`/workspace/node_modules` path.

The frontend quality-gate script continues to run:

    pnpm install --frozen-lockfile

on every build before Vitest, Oxlint, TypeScript, and the Vite production
build. The install remains authoritative for lockfile correctness; the
volume only avoids reconstructing an equivalent dependency tree from scratch.
If the lockfile changes, pnpm updates the volume as part of that install. If
the volume becomes stale or corrupted, removing the named volume restores a
clean install path without changing the pipeline.

The existing pnpm store volume remains mounted and configured through
`PNPM_STORE_DIR`. Workspace cleanup may remove the bind-mounted workspace, but
it must not remove either named dependency volume.

### Bounded backend concurrency

After the existing backend dependency synchronization and Pyright runtime
check complete, start Pytest and the final Pyright check concurrently inside
the existing backend quality-gate container. Ruff check and Ruff format remain
unchanged and execute as explicit gates.

The shell orchestration must retain each command's exit status. It should:

1. Start Pyright in the background and retain its process ID.
2. Run the full Pytest command, including JUnit and coverage output.
3. Wait for Pyright and capture its exit status.
4. Fail the branch if either Pytest or Pyright failed.
5. Continue to emit the existing per-gate timing records.

This is bounded concurrency of two CPU-intensive backend checks. It does not
create unbounded processes or additional containers, and it leaves database
setup, test data, coverage output, Ruff checks, and failure semantics intact.

### Candidate database readiness polling

Change the candidate PostgreSQL readiness loop to poll once per second rather
than once every five seconds. Keep a finite retry limit and the existing
failure behavior, so an unavailable database still fails provisioning rather
than being treated as ready.

The total readiness budget remains bounded and is not replaced with an
unlimited wait. The change only reduces the time between a database becoming
ready and the pipeline noticing it.

### Resource policy

Keep production image builds bounded by the host-capacity logic already in
`deploy/build_images.sh`. On the current deployment host, parallelism remains
one when available memory is below the established threshold. Dependency
volumes reduce network, filesystem, and CPU work; backend concurrency is
limited to the two checks described above.

## Failure handling and recovery

- Any failed quality gate continues to fail the pipeline.
- A failed background Pyright process cannot be hidden by a successful
  Pytest process; both statuses must be checked.
- JUnit and coverage files continue to be written by Pytest before the branch
  reports its result.
- A dependency-volume failure can be recovered by deleting the named volume;
  the next build performs a clean frozen install.
- Database readiness failure continues to stop candidate provisioning and
  invoke the existing failed-stack cleanup path.
- No change is made to router preservation, write-lock recovery, promotion,
  or public-endpoint verification.

## Verification and measurement

Add or update static deployment tests to verify that:

- the frontend dependency volume is declared and mounted;
- the frontend script still uses a frozen-lockfile install;
- Pytest and Pyright are both present and their statuses are aggregated;
- readiness polling is frequent but remains bounded;
- existing timing, JUnit, coverage, and branch-overlap assertions remain
  present.

Run the complete local quality-gate test coverage that is supported by the
development environment, then run Jenkins builds on the target Linux host.
Record at least ten successful post-change builds, including warm-cache and
cold-cache samples, using the existing `docs/ci-cd-baseline.md` measurement
format. Compare total execution time, quality-gate time, resource usage,
image work, and deployment success rate against the baseline.

The two-minute objective is an operational acceptance target. It is not a new
hard quality gate because host load, Docker cache state, and Jenkins queue time
are external variables.

## Acceptance criteria

- All existing backend and frontend gates pass with their evidence artifacts.
- Existing deployment recovery and public-endpoint checks remain unchanged in
  behavior.
- Warm-cache Jenkins builds consistently complete below two minutes on the
  target host, subject to queue time being measured separately.
- No sustained increase in deployment-host resource pressure or failed-build
  rate is observed.
- The post-change measurements identify any remaining critical-path stage if
  the target is not reached by this conservative optimization.
