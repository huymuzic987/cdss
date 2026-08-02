# CI/CD performance baseline

This document defines the measurements required before changing pipeline
concurrency, caching, or deployment behavior. Collect at least ten successful
main builds, including both warm-cache and cold-cache runs.

## Timing sources

Jenkins already records the duration of every top-level stage. The deployment
scripts also emit machine-readable tab-separated records:

    CDSS_TIMING  <operation>  <elapsed-seconds>  <exit-status>

Search the console log for CDSS_TIMING to extract the detailed measurements.
Timing output is intentionally log-only and cannot make a successful operation
fail. A nonzero final field is the wrapped operation's original exit status.
The provisioning script also emits the source database size as:

    CDSS_METRIC  source-database-size-bytes  <bytes>

Detailed timing currently covers:

- pregnancy FHIR catalog generation and schema migration;
- backend dependency sync, pytest, Ruff, and Pyright;
- frontend Vitest, Oxlint, TypeScript, and Vite build gates;
- production backend/frontend image builds;
- candidate database startup, readiness, clone, migration, and seed;
- candidate application startup and health readiness.

Use Jenkins stage duration for checkout, file verification, rsync, environment
injection, route repair, backup, promotion, pruning, public verification, and
post-build cleanup.

## Build classification

For each sampled build, record:

- Jenkins build number and Git commit;
- successful, failed, or aborted result;
- cold or warm dependency cache;
- cold build, partial image rebuild, or full image reuse;
- database size before cloning;
- whether backend, frontend, database, or deployment files changed;
- total queue and execution duration.

Do not combine failed timings with successful-build percentiles. Failed-build
timings remain useful for identifying time-to-feedback and cleanup cost.

## Baseline table

Populate one row per successful build:

| Build | Commit | Cache state | Image work | DB size | Queue | Total | Quality gates | Image build | DB clone | Provision | Public verify |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| | | | | | | | | | | | |

All durations are seconds. Record zero for an intentionally skipped operation
and N/A when no timing record exists.

## Summary metrics

After at least ten successful builds, calculate:

| Metric | Median | P95 |
| --- | ---: | ---: |
| Queue duration | | |
| Total execution | | |
| Backend pytest | | |
| Frontend Vitest | | |
| Frontend production build | | |
| Image build | | |
| Database clone | | |
| Candidate provisioning | | |
| Public verification | | |

Also record:

- deployment success rate;
- warm-cache versus cold-cache quality-gate duration;
- image reuse rate;
- median backup size and duration;
- production disk use immediately before and after pruning.

## Phase acceptance

The baseline is ready for optimization when:

1. Ten successful main builds have been sampled.
2. At least two samples are cold-cache builds.
3. At least two samples rebuild both application images.
4. Database clone duration and database size are recorded together.
5. Slow operations can be identified without reading unstructured log blocks.

Future phase results should add an after-change table here rather than replacing
the original baseline.
