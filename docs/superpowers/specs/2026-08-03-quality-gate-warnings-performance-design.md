# Quality-gate warnings and frontend performance design

## Context

The phase-10 quality-gate run passed all backend and frontend gates, but its
output exposed two Oxlint warnings, one Starlette/httpx compatibility warning,
and a Vite bundle-size warning. Vitest also reports per-test durations; several
showcase and modal tests are materially slower than the rest of the suite.

The goal is to leave the quality-gate output clean, reduce avoidable frontend
work, and preserve all existing runtime and test behavior.

## Goals

- Remove the `react(only-export-components)` warning from the clinical-result
  component module.
- Remove the `eslint(no-control-regex)` warning without changing `cleanText`
  output.
- Use the Starlette-supported `httpx2` test client dependency and keep the
  existing FastAPI `TestClient` test API unchanged.
- Split heavy `tldraw` and `elkjs` modules into bounded, cacheable Vite/Rolldown
  chunks while keeping the canvas lazy-loaded.
- Reduce unnecessary showcase patient-card rerenders during theme and query
  changes.
- Preserve the existing timing records as diagnostics; do not turn normal
  host- or runner-dependent durations into flaky hard failures.

## Non-goals

- Replacing the tldraw canvas or changing canvas behavior.
- Virtualizing the patient list or changing its visible catalog and search
  semantics.
- Hiding warnings with broad lint or pytest suppression rules.
- Removing, selecting, or weakening any quality gate.
- Adding a hard threshold for individual Vitest test durations.

## Design

### Source warning cleanup

Move `isSingleMedicationOrder` from `RecommendedOrderCard.tsx` into a small
clinical-result classification module. Import it from both the modal and the
card, leaving the component module's exports component-only so React Fast
Refresh no longer warns.

Replace the ASCII-range expression in `cleanText` with the equivalent Unicode
escaped range. The replacement and repeated-hyphen collapse remain unchanged.
Focused unit tests will cover empty input, ASCII text, non-ASCII replacement,
and repeated separators.

### Backend test-client compatibility

Replace the development dependency on `httpx` with `httpx2`, regenerate the
lockfile, and retain imports through `fastapi.testclient`. This follows the
warning emitted by the installed Starlette version while minimizing test-code
changes. The backend API test suite remains the compatibility check.

### Frontend chunking

Configure Vite 8's Rolldown output code-splitting groups for the `tldraw` and
`elkjs` dependency trees with a bounded maximum chunk size. The existing
dynamic import of `TreeCanvas` remains the route boundary, so the heavy canvas
runtime is still deferred from the initial application module. Build output
will be inspected to confirm the oversized warning is removed or materially
reduced and that generated chunks remain loadable.

Add a source-level architecture test that protects the code-splitting groups,
the canvas lazy boundary, and the absence of eager tldraw imports in static
side panels.

### Showcase rerender performance

Extract the repeated patient-card markup into a memoized component and make the
showcase patient-selection callback stable. Theme changes and unrelated parent
renders can then reuse unchanged cards; selection and search behavior remain
the same. Existing showcase tests will cover the catalog, selection, retry,
and theme behavior.

### Verification

Use a failing-first cycle for each behavior change:

1. Add focused regression and architecture assertions.
2. Run them and confirm the intended failures.
3. Implement the smallest changes that satisfy them.
4. Run focused tests, Oxlint, TypeScript, and Vite build.
5. Run the complete frontend suite and backend suite, checking for zero lint,
   deprecation, and build warnings where the repository controls the source.

The final report will distinguish test-duration diagnostics from quality-gate
failures and will include the generated bundle sizes observed in verification.
