# CI Failure Remediation and Console Log Reduction Design

## Goal

Restore the Jenkins quality gate for commit `feabefaf` while keeping the
canonical decision-tree data model and making the live Jenkins console useful
for triage. Complete diagnostic output remains available as archived CI
artifacts.

## Source-of-truth and identity

`backups/seed.sql` remains the canonical decision-tree source. The checked-in
JSONB tree snapshots and generated pregnancy FHIR catalogs are derived data;
they will be regenerated from the SQL seed after the canonical node-key
migration. Scenario tests and preset metadata will use the canonical node keys
rather than restoring the stale abbreviated aliases.

FHIR action IDs are a separate wire-format identifier. Node keys are preserved
in the node-key extension, while the FHIR `id` and `relatedAction.actionId`
values use a deterministic slug. IDs at or below 64 characters remain
unchanged. Longer IDs are truncated and receive a stable hash suffix so they
remain valid under the FHIR R4 schema and continue to resolve references.

## Application fixes

The backend FHIR schema test suite will cover the long-ID behavior. The
medication-regimen step helpers will move to a focused module so the existing
200-line behavior-module limit remains meaningful. The frontend regimen catalog
popup will likewise move out of `RegimenDisplay.tsx`, preserving its public
component API and behavior. The medication follow-up order section will use the
computed displayed orders, including the current regimen injected for a
follow-up-only result. The seeded-link test will recognize any actionable node
with a payload, including the canonical inference nodes used by the current
seed.

## CI/CD logging

The quality-gate scripts will write full command output to `.ci-reports` log
files. The live console will show gate names, durations, statuses, and a bounded
tail only when a gate fails. Vitest will use a compact reporter in addition to
its JUnit reporter. Jenkins will archive the log files with the existing JUnit,
coverage, and timing artifacts. File verification and setup diagnostics will be
reduced to concise status lines without removing validation.

## Verification

Implementation follows test-first sequencing:

1. Add focused regression tests for FHIR ID bounds and follow-up order display.
2. Regenerate derived decision-tree and pregnancy artifacts.
3. Run focused backend/frontend tests and architecture checks.
4. Run the complete backend and frontend quality gates, including formatting,
   schema validation, and generated-data consistency.

No deployment stage is changed beyond report/log handling; deployment remains
blocked whenever a quality gate fails.
