# Quality-gate warnings and frontend performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the reported quality-gate warnings and reduce avoidable frontend bundle and showcase rerender costs without changing clinical behavior.

**Architecture:** Keep clinical order classification in a small pure module, keep React component modules component-only, and preserve the existing lazy `TreeCanvas` boundary. Configure Vite 8/Rolldown to split the heavy tldraw and elkjs dependency trees, and memoize stable showcase patient cards behind a stable selection callback.

**Tech Stack:** TypeScript, React 19, Vitest, Testing Library, Oxlint, Vite 8/Rolldown, FastAPI/Starlette, uv, pytest.

## Global Constraints

- Preserve `cleanText` output exactly.
- Preserve the existing FastAPI `TestClient` test API.
- Keep the canvas dynamically imported from `TreeWorkspace`.
- Keep all backend and frontend quality gates enabled.
- Do not add a hard threshold for individual Vitest test durations.
- Do not virtualize the patient catalog or change search semantics.
- Leave the existing `.worktrees/` untracked state untouched.

---

## File Map

- Create `frontend/src/panels/clinicalResult/orderClassification.ts` for the pure medication-order predicate.
- Create `frontend/src/panels/clinicalResult/orderClassification.test.ts` for predicate regression coverage.
- Create `frontend/tests/architecture/cleanText.test.ts` for cleaning behavior and source-level lint intent.
- Modify `frontend/src/panels/clinicalResult/RecommendedOrderCard.tsx` and `frontend/src/panels/TraversalResultModal.tsx` to consume the predicate module.
- Modify `frontend/src/utils/cleanText.ts` to use the Unicode-escaped range.
- Modify `pyproject.toml` and `uv.lock` to use `httpx2` for the Starlette test client.
- Modify `frontend/vite.config.ts` with bounded Rolldown dependency groups.
- Modify `frontend/src/layout/elkLayout.ts` to load ELK's API and worker asset separately.
- Modify `frontend/tests/architecture/performanceBoundaries.test.ts` with code-splitting and memoization invariants.
- Modify `frontend/src/showcase/ShowcaseChrome.tsx` and `frontend/src/showcase/ShowcasePage.tsx` to reduce unnecessary card rerenders.

### Task 1: Extract order classification and remove Oxlint warnings

**Files:**
- Create: `frontend/src/panels/clinicalResult/orderClassification.ts`
- Create: `frontend/src/panels/clinicalResult/orderClassification.test.ts`
- Create: `frontend/tests/architecture/cleanText.test.ts`
- Modify: `frontend/src/panels/clinicalResult/RecommendedOrderCard.tsx`
- Modify: `frontend/src/panels/TraversalResultModal.tsx`
- Modify: `frontend/src/utils/cleanText.ts`

**Interfaces:**
- Produces `isSingleMedicationOrder(order: { orderType?: string; drugClasses?: Array<{ code: string }> }): boolean`.
- `RecommendedOrderCard` and `TraversalResultModal` import the predicate from `./clinicalResult/orderClassification`.

- [ ] **Step 1: Write the failing predicate tests.**

Create `frontend/src/panels/clinicalResult/orderClassification.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { isSingleMedicationOrder } from './orderClassification'

describe('isSingleMedicationOrder', () => {
  it('accepts a medication order without an ABCD combination', () => {
    expect(isSingleMedicationOrder({ orderType: 'medication', drugClasses: [{ code: 'A' }] })).toBe(true)
    expect(isSingleMedicationOrder({ orderType: 'medication', drugClasses: [{ code: 'ARB' }, { code: 'CCB' }] })).toBe(true)
  })

  it('rejects current regimens and ABCD combination therapy', () => {
    expect(isSingleMedicationOrder({ orderType: 'current-regimen', drugClasses: [{ code: 'A' }] })).toBe(false)
    expect(isSingleMedicationOrder({ orderType: 'medication', drugClasses: [{ code: 'A' }, { code: 'C' }] })).toBe(false)
  })
})
```

- [ ] **Step 2: Run the new predicate test and verify the intended failure.**

Run from `frontend/`:

```bash
pnpm exec vitest run src/panels/clinicalResult/orderClassification.test.ts
```

Expected: FAIL because `orderClassification.ts` does not exist yet.

- [ ] **Step 3: Write the cleaning regression tests and lint-source assertion.**

Create `frontend/tests/architecture/cleanText.test.ts`:

```ts
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { cleanText } from './cleanText'

describe('cleanText', () => {
  it('preserves ASCII text and trims it', () => {
    expect(cleanText('  Blood pressure  ')).toBe('Blood pressure')
  })

  it('replaces non-ASCII runs and collapses repeated separators', () => {
    expect(cleanText('  Tăng huyết áp — urgent  ')).toBe('T-ng huy-t p-urgent')
  })

  it('returns an empty string for empty input', () => {
    expect(cleanText('')).toBe('')
  })

  it('uses Unicode escapes for the ASCII range', () => {
    const source = readFileSync(new URL('./cleanText.ts', import.meta.url), 'utf8')
    expect(source).toContain('[^\\u0000-\\u007F]')
    expect(source).not.toContain('[^\\x00-\\x7F]')
  })
})
```

Run it before changing production code:

```bash
pnpm exec vitest run src/utils/cleanText.test.ts
```

Expected: the behavior tests pass, while the source-intent assertion fails because the current regex uses `\x00`/`\x7F`. This is the required red check for a lint-only change.

- [ ] **Step 4: Implement the smallest source-warning fix.**

Move the existing predicate unchanged into `orderClassification.ts`:

```ts
export function isSingleMedicationOrder(order: {
  orderType?: string
  drugClasses?: Array<{ code: string }>
}): boolean {
  const isAbcdCombination = (order.drugClasses?.length ?? 0) > 1
    && order.drugClasses!.every((item) => /^[ABCD]$/.test(item.code))
  return order.orderType === 'medication' && !isAbcdCombination
}
```

Import it into `RecommendedOrderCard.tsx` and `TraversalResultModal.tsx`, remove the duplicate/local export, and replace the clean-text pattern with `/[^\u0000-\u007F]+/gu`.

- [ ] **Step 5: Run the focused tests and Oxlint.**

```bash
pnpm exec vitest run src/panels/clinicalResult/orderClassification.test.ts src/utils/cleanText.test.ts src/panels/TraversalResultModal.test.tsx
pnpm exec oxlint
```

Expected: all focused tests pass and Oxlint reports zero warnings and zero errors.

- [ ] **Step 6: Commit the warning cleanup.**

```bash
git add frontend/src/panels/clinicalResult/orderClassification.ts frontend/src/panels/clinicalResult/orderClassification.test.ts frontend/src/panels/clinicalResult/RecommendedOrderCard.tsx frontend/src/panels/TraversalResultModal.tsx frontend/src/utils/cleanText.ts frontend/src/utils/cleanText.test.ts
git commit -m "fix(frontend): remove quality gate lint warnings"
```

### Task 2: Remove the Starlette/httpx compatibility warning

**Files:**
- Modify: `pyproject.toml` development dependencies
- Modify: `uv.lock` through `UV_CACHE_DIR=/tmp/cdss-uv-cache uv lock`

**Interfaces:**
- Keeps all existing `from fastapi.testclient import TestClient` imports unchanged.
- Produces a frozen lockfile containing `httpx2` and no longer relies on the deprecated `httpx` fallback.

- [ ] **Step 1: Add the direct test-client dependency.**

Change the development dependency line in `pyproject.toml` from:

```toml
"httpx>=0.27",
```

to:

```toml
"httpx2>=1.0",
```

- [ ] **Step 2: Regenerate the lockfile.**

Run:

```bash
UV_CACHE_DIR=/tmp/cdss-uv-cache uv lock
```

Expected: `uv.lock` records `httpx2` and its compatible transport dependencies, with no unresolved lock error.

- [ ] **Step 3: Verify the backend client imports without the deprecation warning.**

Run:

```bash
PYTHONWARNINGS=error .venv/bin/python -c "from fastapi.testclient import TestClient; print(TestClient.__name__)"
```

Expected: exit 0 and print `TestClient` without raising `StarletteDeprecationWarning`.

- [ ] **Step 4: Run API tests.**

```bash
.venv/bin/pytest -q tests/api
```

Expected: API tests pass with no warnings summary for the test client.

- [ ] **Step 5: Commit the dependency update.**

```bash
git add pyproject.toml uv.lock
git commit -m "fix(test): use httpx2 with Starlette TestClient"
```

### Task 3: Bound heavy frontend dependency chunks

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/layout/elkLayout.ts`
- Modify: `frontend/tests/architecture/performanceBoundaries.test.ts`

**Interfaces:**
- Produces named Rolldown output groups for `tldraw` and `elkjs`, each with `maxSize: 450 * 1024`.
- Loads `elkjs/lib/elk-api.js` with `elkjs/lib/elk-worker.min.js?url` instead of bundling `elk.bundled.js`.
- Preserves `TreeWorkspace`'s `lazy(() => import('../canvas/TreeCanvas'))` boundary.

- [ ] **Step 1: Add failing source-boundary assertions.**

Extend `frontend/tests/architecture/performanceBoundaries.test.ts`:

```ts
it('bounds the heavy canvas dependency chunks', () => {
  const vite = read('vite.config.ts')
  expect(vite).toContain("name: 'tldraw'")
  expect(vite).toContain("name: 'elkjs'")
  expect(vite).toContain('maxSize: 450 * 1024')
})

it('memoizes showcase patient cards and selection callbacks', () => {
  expect(read('src/showcase/ShowcaseChrome.tsx')).toMatch(/memo\(function PatientCard/)
  expect(read('src/showcase/ShowcasePage.tsx')).toContain('const selectPatient = useCallback(')
})
```

- [ ] **Step 2: Run the architecture tests and verify the intended failure.**

```bash
pnpm exec vitest run tests/architecture/performanceBoundaries.test.ts
```

Expected: the two new assertions fail because the Vite groups and memoized card do not exist yet.

- [ ] **Step 3: Add bounded Rolldown groups.**

Add this configuration to `frontend/vite.config.ts`:

```ts
const CANVAS_CHUNK_MAX_SIZE = 450 * 1024
const CANVAS_DEPENDENCY_GROUPS = [
  {
    name: 'tldraw',
    test: /node_modules[\\/]tldraw[\\/]/,
    minSize: 20 * 1024,
    maxSize: CANVAS_CHUNK_MAX_SIZE,
    priority: 2,
  },
  {
    name: 'elkjs',
    test: /node_modules[\\/]elkjs[\\/]/,
    minSize: 20 * 1024,
    maxSize: CANVAS_CHUNK_MAX_SIZE,
    priority: 1,
  },
]
```

Set `build.rolldownOptions.output.codeSplitting.groups` to that constant while preserving the existing plugins and server configuration.

- [ ] **Step 4: Memoize showcase cards and stabilize selection.**

In `ShowcaseChrome.tsx`, import `memo`, extract the existing patient-card JSX into a non-exported `memo(function PatientCard({ patient, selected, onSelect }: { patient: ShowcasePatient; selected: boolean; onSelect: (patient: ShowcasePatient) => void }) { ... })`, and render it from `PatientQueue`.

In `ShowcasePage.tsx`, import `useCallback` and replace the inline selection function with:

```ts
const selectPatient = useCallback((patient: ShowcasePatient) => {
  setSelectedPatient(patient)
  void runEvaluation(patient)
}, [runEvaluation])
```

- [ ] **Step 5: Run architecture tests and the production build.**

```bash
pnpm exec vitest run tests/architecture/performanceBoundaries.test.ts
pnpm exec tsc -b
pnpm exec vite build
```

Expected: architecture and TypeScript checks pass; the build completes without the previous 3.1 MB `TreeCanvas` chunk warning. Record the generated chunk sizes for the final report. If Rolldown keeps an individual third-party module above the configured limit, retain the lazy boundary and report the remaining measured chunk rather than increasing the warning threshold blindly.

- [ ] **Step 6: Commit the performance changes.**

```bash
git add frontend/vite.config.ts frontend/tests/architecture/performanceBoundaries.test.ts frontend/src/showcase/ShowcaseChrome.tsx frontend/src/showcase/ShowcasePage.tsx
git commit -m "perf(frontend): split canvas dependencies and memoize showcase cards"
```

### Task 4: Full regression verification

**Files:**
- Read: all changed files and generated build output
- Test: frontend and backend quality-gate commands

- [ ] **Step 1: Run the complete frontend suite.**

```bash
cd frontend
pnpm exec vitest run
pnpm exec oxlint
pnpm exec tsc -b
pnpm exec vite build
```

Expected: all frontend tests pass, Oxlint has zero warnings/errors, TypeScript exits 0, and Vite exits 0 without the oversized-chunk warning.

- [ ] **Step 2: Run the complete backend suite and format/static checks.**

```bash
cd ..
.venv/bin/pytest -q
.venv/bin/ruff check
.venv/bin/ruff format --check
.venv/bin/pyright
```

Expected: backend tests and all static checks pass without the Starlette/httpx deprecation warning.

- [ ] **Step 3: Inspect the final diff and status.**

```bash
git diff --check
git status --short
git log -6 --oneline
```

Confirm only the approved implementation files and the committed design/plan documents changed; do not stage or remove `.worktrees/`.

- [ ] **Step 4: Report measured evidence.**

Report test counts, lint/build status, the absence or exact measured status of any remaining Vite warning, and explain that individual yellow Vitest durations are observational rather than hard failures.
