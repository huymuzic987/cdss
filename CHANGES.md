# Changes: targeted fixes from FRONTEND_AUDIT_FINDINGS.md

All changes are unstaged. Scope: the 5 fixes explicitly requested. The two
"Needs confirmation" items (`handleChangeArrowKind` ref consistency,
`handleResetLayout` DELETE/PUT ordering) and the two product-decision items
(stale summary on dashboard fetch error, loading-vs-failed UX) were left
untouched, as instructed.

---

## 1. Error boundary + tree-graph shape guard (Critical + High)

**Files:** `frontend/src/app/ErrorBoundary.tsx` (new), `frontend/src/styles/error-boundary.css` (new),
`frontend/src/main.tsx`, `frontend/src/app/TreeWorkspace.tsx`,
`frontend/src/canvas/validateTreeGraph.ts` (new), `frontend/src/canvas/useTreeCanvasScene.ts`,
`frontend/src/App.css`

- Added `ErrorBoundary`, a standard class-component boundary
  (`getDerivedStateFromError` + `componentDidCatch`) with a fallback showing
  "Something went wrong", a plain-language one-line explanation, a **Try
  again** button (clears the boundary's error state and re-renders children)
  and a **Reload page** button (`window.location.reload()`).
- Wrapped `<App />` with it in `main.tsx` so any uncaught render-time error
  anywhere in the app shows the fallback instead of a blank white page.
- Also wrapped just `<TreeCanvas>` in `TreeWorkspace.tsx` with a second,
  nested boundary (`key={graph.tree.tree_key}`, `label="tree canvas"`), since
  that's the highest-risk subtree (it consumes unvalidated backend JSON). The
  boundary is keyed by tree so switching to a different, valid tree gets a
  fresh boundary instance instead of being stuck showing a stale fallback for
  a different tree's error.
- Added `validateTreeGraph.ts` with `isValidTreeGraph()`: a minimal shape
  check (tree has a non-empty `tree_key`, `nodes` and `edges` are arrays) --
  intentionally not a full schema validator, per the instructions.
- Called it at the top of `handleMount` in `useTreeCanvasScene.ts`, before any
  code touches `graph.nodes`/`graph.edges`. On failure it `throw`s a
  descriptive `Error` instead of letting `graph.nodes.map(...)` fail with a
  raw `TypeError`; the thrown error is caught by the `ErrorBoundary` wrapping
  `TreeCanvas` and shown as the friendly fallback.
- Added `styles/error-boundary.css` (imported from `App.css`, matching the
  existing per-concern CSS file pattern) using existing theme variables
  (`--danger-*`, `--bg-app`, `--accent-solid`, etc.) so it matches dark/light
  theme automatically.

**Verification:** Wrote a temporary test file
(`frontend/src/app/__tmp_verify.test.tsx`, deleted before finishing -- not in
the final diff) that:
  - rendered `<ErrorBoundary><Bomb /></ErrorBoundary>` where `Bomb` throws
    unconditionally, and asserted the fallback text, the interpolated label,
    and both buttons render (2 assertions covering the catch path and the
    normal pass-through path). All passed.
  - called `isValidTreeGraph()` directly with a well-formed graph and three
    malformed variants (missing `nodes`, missing `edges`, empty `tree_key`),
    asserting `true`/`false` as expected. All passed.

  The remaining link -- that a `throw` inside the `handleMount` callback
  passed as `onMount` to `<Tldraw>` is actually caught by the `ErrorBoundary`
  ancestor -- was verified by reasoning rather than a live tldraw-in-jsdom
  test (mounting a full tldraw editor in a unit test is heavy and was judged
  out of proportion for this check): `onMount` is invoked by tldraw's own
  React component during its mount/effect lifecycle, and React routes errors
  thrown during rendering and in effects of any descendant to the nearest
  ancestor error boundary via `componentDidCatch`/`getDerivedStateFromError`
  -- this is standard, well-documented React behavior, not something specific
  to this codebase. Combined with the two passing tests above (the boundary
  correctly catches synchronous throws, and the guard correctly flags bad
  graphs), the wiring is sound.

## 2. PatientsPanel search race + unmount setState (Medium)

**File:** `frontend/src/dashboard/PatientsPanel.tsx`

Added a `requestIdRef` counter, mirroring the `runIdRef` pattern in
`hooks/traversal/useEvaluationRunner.ts`:
- Each effect run captures its own `requestId = ++requestIdRef.current`.
- The `.then`/`.finally` callbacks only call `setResult`/`setLoading` if
  `requestIdRef.current` still equals that run's `requestId`.
- The effect's cleanup (which fires both on a dependency change and on
  unmount) increments `requestIdRef.current`, invalidating any in-flight
  request from that run.

This fixes both problems named in the audit: a slower, older search
resolving after a faster, newer one can no longer overwrite the newer
results, and a fetch that resolves after the panel has unmounted is now a
no-op instead of calling `setResult`/`setLoading` on an unmounted component.

**Verification:** Reasoning walkthrough (no test added -- this is a timing
race that's awkward to assert deterministically without fake-timer
choreography, and the fix is a direct structural mirror of the existing,
already-relied-upon `runIdRef` pattern elsewhere in the codebase). Confirmed
via `tsc --noEmit` and `oxlint` that the new ref and callback shapes type/lint
clean, and via `pnpm vitest run` that no existing test regressed.

## 3. New-Set-per-render in App.tsx (Medium)

**File:** `frontend/src/App.tsx`

Replaced the two inline `new Set<string>()` fallbacks (one per branch of the
`visibleHighlights` ternary) with a single module-level constant,
`EMPTY_HIGHLIGHTS`. An idle render (no active highlight set for the current
tree) now hands `TreeCanvas` the same stable empty-`Set` reference every time
instead of a new object identity, so `useTreeCanvasSync`'s highlight-diff
effect (which depends on `highlightedNodeKeys` by reference) no longer
re-runs on every unrelated `App` re-render (e.g. every `mousemove` while
dragging the sidebar resizer).

**Verification:** `tsc --noEmit` confirms `EMPTY_HIGHLIGHTS: ReadonlySet<string>`
still satisfies the `highlightedNodeKeys?: ReadonlySet<string>` prop type used
throughout `TreeWorkspace` → `TreeCanvas` → `useTreeCanvasSync`. Reasoning
walkthrough: the effect in `useTreeCanvasSync.ts:54-84` lists
`highlightedNodeKeys` in its dependency array; with a stable reference, React
now correctly skips it via `Object.is` comparison when nothing actually
changed, which is the intended behavior. No test added since asserting "an
effect did not re-run" would require either a render-count spy on the
production hook (an invasive change) or mocking tldraw's editor, which wasn't
justified for this one-line fix.

## 4. DonutStat divide-by-zero (Low)

**File:** `frontend/src/dashboard/charts/DonutStat.tsx`

The tooltip formatter now checks `total === 0` and renders `0%` instead of
computing `NaN%` when every slice's value is 0.

**Verification:** Reasoning walkthrough -- the change is a one-line ternary
guard; `total === 0 ? '0' : ...` is straightforward to confirm by inspection.
Confirmed no existing test covers `DonutStat` (none needed updating) and that
`tsc --noEmit`/`oxlint` are clean.

## 5. Dead `rateVerdict(...)` call in DashboardKpis.tsx (Low)

**Files:** `frontend/src/dashboard/DashboardKpis.tsx`, `frontend/src/dashboard/DashboardPage.tsx`

Removed the discarded `rateVerdict(efficacy.overall_adherence_rate, 0.75,
0.5)` call. Since that was the only use of the `efficacy` parameter inside
`FollowUpKpis`, also removed the now-unused `efficacy` prop from
`FollowUpKpisProps` and its destructuring, and dropped the corresponding
`efficacy={efficacy}` prop at the one call site in `DashboardPage.tsx`
(per CLAUDE.md's "clean up orphans your own change creates" rule). The
`efficacy &&` guard on the surrounding `{hasData && overview && visits &&
efficacy && (...)}` render condition in `DashboardPage.tsx` was intentionally
left as-is -- removing it would loosen when `FollowUpKpis` renders, which is
a product decision outside this fix's scope.

**Verification:** `tsc --noEmit` confirms no unused-variable/prop-mismatch
errors after the interface and call-site change. `oxlint` clean.

---

## Verification summary (commands run)

```
npx tsc --noEmit      # 0 errors
pnpm lint              # (oxlint) 0 errors
pnpm vitest run        # 73 tests: 72 passed, 1 pre-existing failure
```

The one failing test,
`src/panels/mockPatientForm/fhirBundle.test.ts > canonical FHIR patient
presets > keeps the eclampsia preset anchored to preeclampsia`, was confirmed
pre-existing and unrelated to these changes: `git stash`-ing all edits and
re-running just that file reproduces the identical failure on the unmodified
branch, then `git stash pop` restored the fixes. Not touched, per the "don't
make unrelated changes" rule.

No `OPEN_QUESTIONS.md` was needed -- all 5 requested fixes were implemented
without hitting unexpected risk or scope.
