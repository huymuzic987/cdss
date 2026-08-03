# CI Failure Remediation Implementation Plan

> Execute this plan task-by-task with test-first checkpoints.

## 1. Add regression coverage

- Add a backend FHIR schema test for a long node key that verifies the emitted
  action ID is deterministic, valid, at most 64 characters, and reused by
  related-action references.
- Preserve the existing frontend follow-up order tests and add only the
  smallest assertion needed if the current failure does not already cover the
  regression.
- Run the focused tests to establish the expected red state before production
  changes.

## 2. Align generated decision-tree data

- Replace stale abbreviated pregnancy expected-node keys in
  `scripts/generate_pregnancy_fhir_presets.py` with the canonical keys in
  `backups/seed.sql`.
- Export all JSONB snapshots from `backups/seed.sql` with
  `scripts/export_trees_to_jsonb.py`.
- Regenerate pregnancy FHIR JSON files and the frontend generated catalog.
- Update hardcoded scenario expectations and seeded-link assertions to match
  the canonical graph and actionable inference-node model.
- Run JSONB-vs-SQL and seeded traversal tests.

## 3. Implement backend fixes

- Add stable, schema-safe FHIR ID shortening with a hash suffix and use it for
  both action IDs and references.
- Move medication-regimen step parsing/helpers into a focused module and keep
  the existing public API unchanged.
- Format changed Python files with Ruff.
- Run the FHIR, regimen, architecture, and mock-scenario tests.

## 4. Implement frontend fixes

- Make the medication/order empty-state check use `displayedOrders`, so a
  current follow-up regimen is rendered.
- Move catalog-popup rendering/helpers out of `RegimenDisplay.tsx` while
  preserving props, accessibility behavior, and catalog interactions.
- Run the focused TraversalResultModal, showcase, and source-size tests; then
  run the complete frontend suite.

## 5. Reduce CI console output and retain artifacts

- Add bounded failure-tail logging to backend and frontend gate wrappers.
- Redirect complete gate output to `.ci-reports` logs and use Vitest’s compact
  reporter plus JUnit output.
- Make Jenkins file verification and setup messages concise.
- Ensure Jenkins archives all generated logs in addition to JUnit, coverage,
  and timing files.
- Add or update pipeline tests for report archiving and concise gate behavior.

## 6. Verify before handoff

- Run backend formatting, static checks, and the full test suite.
- Run frontend lint, type check, build, and the full test suite.
- Run the repository’s quality-gate/deployment-script tests.
- Inspect `git diff`, generated-file consistency, and remaining stale ID
  references. Report any environment-only limitation separately.
