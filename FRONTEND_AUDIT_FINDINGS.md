# Frontend Static Bug-Review Audit

Scope: `frontend/src` (read-only, no code changes). Traced actual code paths across
the tree-canvas stack (`hooks/useTreeGraphs.ts`, `hooks/traversal/*`,
`canvas/*`, `app/*`), the dashboard stack (`dashboard/*`), the API client
(`api/client.ts`, `api/types.ts`), and the shared panels (`panels/*`).

Context: `canvas/*` was split from a god-file in commit `f5ca361` ("split god-file
components into focused modules"); `hooks/traversal/*` and several `dashboard/*`
modules were split in commit `5a9c5fc` ("refactor: split oversized source
modules"). Both splits were checked specifically for state/prop drift introduced
by the extraction.

---

## 1. React state management

**No stale-closure bugs found in the traversal or graph-loading hooks.**
`useTraversal`/`useEvaluationRunner` (`hooks/traversal/useEvaluationRunner.ts`)
use a `runIdRef` token that is checked after every `await` boundary
(lines 28, 34, 43), which correctly discards results from a superseded run
instead of writing stale data into state. `useTreeGraphs.ts` keys its
`graphCache` by `tree_key` (line 16), so out-of-order resolution across tabs
cannot overwrite a different tree's data (see Race Conditions, below).

- **Severity: Low — `frontend/src/hooks/useTreeGraphs.ts:65-81` (`handleJumpToLink`)**
  Jumping to a linked node in another tree does not clear `selectedNode` before
  awaiting the target tree's graph fetch. Until the new `TreeCanvas` (remounted
  via `key={graph.tree.tree_key}` in `app/TreeWorkspace.tsx:66`) mounts and
  re-selects the focused shape, `NodeDetailPanel` briefly continues showing the
  previous tree's node details. Self-corrects once the new canvas mounts and
  fires its selection listener; UX-only, not a data-integrity bug.
  Suggested fix direction: `setSelectedNode(null)` alongside `setFocusNodeKey`
  in `handleJumpToLink`.

- **Severity: Low / code-smell — `frontend/src/dashboard/DashboardKpis.tsx:41`**
  `rateVerdict(efficacy.overall_adherence_rate, 0.75, 0.5)` is called and its
  result discarded (no assignment, no use). Dead computation left over from a
  refactor; harmless but should be removed or wired up.

**God-file-split check:** Props/state passed between `useTreeCanvasScene`,
`useTreeCanvasSync`, and `useTreeCanvasControls` (all consuming the same
`editorRef`/`shapeIdsRef`/`lastSaved*Ref` objects) were traced for drift — see
Race Conditions §3 for the one real inconsistency found
(`useTreeCanvasControls.ts:74-88`).

---

## 2. useEffect correctness and memory leaks

**No missing-cleanup issues found.** Every effect that registers a listener,
timer, or subscription tears it down correctly:

| Location | Resource | Cleanup |
|---|---|---|
| `app/TreeTabs.tsx:40-47` | `ResizeObserver` | `observer.disconnect()` |
| `hooks/useSidebarResize.ts:12-34` | `mousemove`/`mouseup` on `window` | both removed |
| `panels/CopyButton.tsx:11-15` | `setTimeout` | cleared on unmount |
| `panels/clinicalResult/RecommendedOrderCard.tsx:31-58` | `resize`/`scroll` listeners + close timer | both removed; `useEffect(() => () => cancelClose(), [])` clears the timer |
| `canvas/useTreeCanvasScene.ts:111-179` | tldraw `editor.store.listen` | `unlisten()` called in the returned cleanup, plus a synchronous `flushSave()` so a fast tab switch doesn't drop the last drag before the 800ms debounce fires |

`useTreeCanvasScene.ts:181-183` intentionally uses an empty dependency array
(with an `eslint-disable-next-line` comment) because `handleMount` is a
tldraw `onMount` callback, not a React effect proper, and `TreeCanvas` is
remounted per tree via `key={graph.tree.tree_key}` (`app/TreeWorkspace.tsx:66`).
Verified this key is actually present, so the "runs once, captures `graph`
from first render" assumption documented in the comment holds — this is not a
stale-closure bug.

- **Severity: Medium — `frontend/src/api/client.ts` (whole file)**
  No `AbortController`/`signal` is used anywhere (`getJson`, `postJson`,
  `putJson`, `postEvaluation`, lines 22-128). Combined with finding §3 below,
  this means in-flight requests are never cancelled on unmount or on
  rapid re-navigation — components rely entirely on `cancelled` boolean flags
  (present in `dashboard/DashboardPage.tsx:31-36` and
  `dashboard/PatientDetailModal.tsx:16-26`, both correct) or, in one case
  (`PatientsPanel.tsx`), on nothing at all. See §3.

- **Severity: Medium — `frontend/src/dashboard/PatientsPanel.tsx:32-46`**
  The debounced search effect has no `cancelled` guard and no abort:
  ```
  useEffect(() => {
    setLoading(true)
    const handle = setTimeout(() => {
      fetchPatients({...}).then(setResult).finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(handle)
  }, [query, gender, status, page])
  ```
  If the component unmounts (e.g. dashboard closed) while a fetch triggered by
  the timeout is already in flight, `setResult`/`setLoading` still run after
  unmount. React 18 no longer warns/crashes on this, so it is not visibly
  destructive, but it is wasted work and, combined with the race in §3, is the
  root cause of that finding.

---

## 3. Race conditions

- **Tree-switch race (graph loading): no issue found.**
  `hooks/useTreeGraphs.ts:40-47` fetches into `graphCache` keyed by the
  specific `treeKey` closed over at effect-invocation time, guarded by an
  `inFlightRef` set (line 39) that prevents duplicate fetches for the same key.
  Because each response is written to its own key rather than to a single
  "current" slot, an old response resolving after a newer one cannot overwrite
  it — switching trees quickly (A → B → A) cannot corrupt `graphCache`. This
  was the primary race scenario asked about and it is handled correctly by
  design.

- **Severity: Medium — `frontend/src/dashboard/PatientsPanel.tsx:32-46`**
  Real race: the 300ms `setTimeout` debounce cancels a *pending* fetch that
  hasn't started yet, but once a fetch is actually in flight (timer fired,
  `fetchPatients` called), there is no request-id or abort mechanism. If the
  user changes the query again immediately after a slow request has started
  (e.g. types "a", waits >300ms so the request fires, then quickly types "ab"),
  the two `fetchPatients(...).then(setResult)` calls can resolve out of order,
  and the response for "a" can overwrite the response for "ab" if it arrives
  later. Manifests as: search results silently reverting to an earlier,
  now-stale query's results.
  Suggested fix direction: track a request token/ref (like `runIdRef` in the
  traversal hooks) and ignore a resolved fetch whose token is stale, or use
  `AbortController` and ignore `AbortError`.

- **Severity: Low / Needs confirmation — `frontend/src/canvas/useTreeCanvasControls.ts:74-88` (`handleChangeArrowKind`)**
  Updates `lastSavedArrowKindRef.current` and `lastSavedEdgeLayoutsRef.current`
  but never writes the freshly computed `positions` into
  `lastSavedPositionsRef.current`, even though those same `positions` are sent
  to the backend via `saveTreeLayout`. In the observed code paths this is
  harmless because `positions` at that moment should already equal what's in
  `lastSavedPositionsRef` (node positions aren't touched by an arrow-kind
  change, and any prior drag would have already updated the ref via the
  `editor.store.listen` callback in `useTreeCanvasScene.ts:134-143`). Flagging
  as needs-confirmation because it's a real structural inconsistency between
  the three "last saved" refs (two are updated here, one isn't) that could
  desync if a future change starts mutating positions in this code path.

- **Severity: Low / Needs confirmation — `frontend/src/canvas/useTreeCanvasControls.ts:90-125` (`handleResetLayout`)**
  Fires `resetTreeLayout` (a `DELETE`) without awaiting it, then immediately
  calls `editor.updateShapes(...)` with freshly computed ELK positions. That
  `updateShapes` call is picked up by `useTreeCanvasScene`'s
  `editor.store.listen` (scope `'user'`), which — since `lastSavedPositionsRef`
  was just cleared to `{}` (line 119) — sees every node as "moved" and
  schedules a debounced `PUT /layout` 800ms later (`useTreeCanvasScene.ts:166`).
  If the `DELETE` response arrives *after* that `PUT`, the reset layout row is
  wiped from the backend right after being recreated. Net effect on next page
  load is likely unobservable (ELK is deterministic given the same graph), but
  the two requests are unordered relative to each other, which is fragile.
  Suggested fix direction: await `resetTreeLayout` before calling
  `editor.updateShapes`, or have `handleResetLayout` set
  `isSceneLoadedRef`-style guard to suppress the listener's auto-save for this
  one programmatic update.

- **Shared mutable refs from multiple effects/callbacks:** `editorRef`,
  `shapeIdsRef`, `lastSavedPositionsRef`, `lastSavedArrowKindRef`,
  `lastSavedEdgeLayoutsRef` are all created in `useTreeCanvasScene` and passed
  by reference into both `useTreeCanvasSync` (read-only) and
  `useTreeCanvasControls` (read/write). No unguarded concurrent-write bug was
  found beyond the two items above — reads in `useTreeCanvasSync` are
  effect-gated on `isSceneLoaded` and don't race with the mount-time writes.

---

## 4. Re-render loops and performance

**No infinite render loops found.** No effect calls `setState` unconditionally
with a dependency on itself.

**ELK layout is not recomputed on every render.** `layoutTree` (expensive) is
only invoked in `useTreeCanvasScene.ts:51` (once, inside `handleMount`, i.e.
once per tree-tab mount) and in `useTreeCanvasControls.ts:98`
(`handleResetLayout`, an explicit user action). It is not on the render path.

- **Severity: Medium — `frontend/src/App.tsx:31-33` → `frontend/src/canvas/useTreeCanvasSync.ts:54-84`**
  ```
  const visibleHighlights = graphs.activeTreeKey
    ? traversal.highlightedNodeKeys[graphs.activeTreeKey] ?? new Set<string>()
    : new Set<string>()
  ```
  When there's no active highlight set for the current tree (the common case
  when idle), a **brand-new `Set` instance** is created on every `App` render
  and passed down as `highlightedNodeKeys` through `TreeWorkspace` →
  `TreeCanvas` → `useTreeCanvasSync`. That prop is a dependency of the
  "Apply highlight status to shapes" effect (`useTreeCanvasSync.ts:54-84`),
  so a new (but semantically identical, empty) `Set` re-triggers the effect,
  which iterates every shape in `shapeIdsRef.current` and calls
  `editor.getShape()` for each. `App` re-renders on every `mousemove` while
  the user drags the right-sidebar resizer (`useSidebarResize.ts` updates
  `width` state on every `mousemove`, and that state is threaded back into
  `App` via the `sidebar` object used for `TreeWorkspace`'s props), so dragging
  the resizer causes this shape loop to run on every mouse-move tick for the
  whole duration of the drag. Likely fine at current node counts (tens of
  nodes) but is unnecessary work and will scale poorly with larger trees.
  Suggested fix direction: memoize a single shared empty `Set` constant instead
  of allocating one inline, or wrap `visibleHighlights`/`visibleActiveNode` in
  `useMemo` keyed on the real inputs.

- No other unmemoized new-object/array/function identities were found being
  passed into `Tldraw`'s `shapeUtils`/`components` (both are module-level
  constants, `canvas/TreeCanvas.tsx:10-27`, correctly stable) or into other
  memoized children.

---

## 5. Out-of-bounds / undefined access

- **Severity: High — no runtime validation anywhere between `fetch` and use (see §6 for the crash-blast-radius consequence).**
  `api/client.ts:22-51` (`getJson`, `postJson`, `putJson`) all do
  `return (await response.json()) as T` — a compile-time-only type assertion.
  Nothing checks that a `TreeGraphResponse` actually has `nodes`/`edges` arrays,
  that a `TreeSummary` has a `tree_key`, etc. Downstream code assumes the shape
  unconditionally, e.g. `canvas/useTreeCanvasScene.ts:47`
  (`graph.nodes.map(...)`) and `:51` (`layoutTree(graph.nodes, graph.edges)`).
  If the backend ever returns a malformed/partial graph (e.g. a schema
  mismatch during a deploy, or a proxy returning a truncated body), these throw
  a plain `TypeError` at render/mount time. See §6 for why this is worse than
  it would normally be.

- **Tree-key lookups:** All the "does this key exist" lookups found are
  correctly guarded with `?? null`/optional chaining, e.g.
  `useTreeGraphs.ts:89` (`activeTreeKey ? graphCache[activeTreeKey] : undefined`),
  `App.tsx:31-33`, `canvas/useTreeCanvasSync.ts` (`shapeIdsRef.current.get(...)`
  checked for `undefined` before use at lines 48, 90). No unguarded
  `lookup[key]!` access was found.

- **Severity: Low — `frontend/src/dashboard/charts/DonutStat.tsx:19,38`**
  `const total = slices.reduce((sum, s) => sum + s.value, 0)` is used as a
  tooltip-percentage denominator (`(Number(v) / total) * 100`) with no
  zero-guard. If every slice's `value` is `0` (a real possibility for e.g. a
  distribution chart on a filtered cohort with no matches in that dimension),
  the tooltip renders `NaN%`. Not a crash, cosmetic only.

- `panels/NodeDetailPanel.tsx:80` uses `node.link_target_tree_key!` — verified
  safe: it's only reachable inside the `node.node_type === 'LINK' &&
  node.link_target_tree_key` guard at line 63, so the non-null assertion
  cannot be hit with a null value given current call sites.

---

## 6. Unhandled errors and validation

- **Severity: Critical — no React Error Boundary exists anywhere in the app.**
  Confirmed via `grep -rn "ErrorBoundary\|componentDidCatch\|getDerivedStateFromError"`
  across the repo: zero matches. `main.tsx` renders `<App />` directly inside
  `<StrictMode>` with no boundary. This means **any** uncaught render-time
  exception — including the malformed-graph-JSON scenario in §5, or an
  internal tldraw error — unmounts the entire React tree, producing a blank
  white page with nothing but a console error. There is no fallback UI, no
  "something went wrong, reload" message, nothing recoverable without a manual
  page refresh.
  Suggested fix direction: wrap `<App />` (or at minimum `<TreeCanvas>`, the
  highest-risk subtree given it consumes unvalidated backend JSON) in an error
  boundary component with a retry/reload affordance.

- **Severity: Medium — `frontend/src/api/client.ts:24-27` etc. (all four request helpers)**
  On a non-OK response, the code unconditionally does
  `const body = (await response.json()) as ApiErrorResponse` to extract
  `body.message`. If the error response isn't valid JSON (e.g. an nginx/proxy
  502 HTML page, or a backend 500 with a non-JSON body), `response.json()`
  itself throws a `SyntaxError`. This is still caught by callers' `.catch`
  blocks (so it doesn't crash the app, thanks to §-worthy defensive callers
  like `useTreeGraphs.ts:35`), but the user sees a generic
  `"Unexpected token < in JSON..."`-style message instead of a meaningful
  "backend unreachable" error.

- **Severity: Needs confirmation — `frontend/src/dashboard/DashboardPage.tsx:30-36`**
  On a failed `fetchDashboardSummary` (e.g. a bad filter combination causing a
  500), `error` is set but `summary` is **not** cleared/reset. The dashboard
  keeps rendering the previous (possibly now-inconsistent-with-filters)
  `summary` underneath the new error banner. This might be intentional
  ("show last-good data with a warning") or might be confusing ("looks like
  the filter had no effect"). Flagging rather than asserting, since both
  readings are plausible product decisions.

- Runtime shape validation of the traversal/evaluation response
  (`EvaluationResponse`/`ApiErrorResponse`) is similarly absent, but all
  consuming code (`clinicalPresentation/*`, `clinicalResult/decisionPath.ts`)
  defensively re-checks types at every access via `objectValue`/`stringValue`
  helpers (`panels/clinicalPresentation/values.ts:4-10`) rather than trusting
  the declared TypeScript types — this part of the codebase is notably more
  defensive than the tree-graph path and does **not** share the crash risk
  described above for malformed `presentation` data; a missing/invalid
  `schema_version` produces a friendly "Invalid clinical presentation
  contract" message (`clinicalDecisionSupportAdapter.ts:40-46`) instead of a
  crash.

---

## 7. Async / loading state

- **Severity: Medium — `frontend/src/app/TreeWorkspace.tsx:64-77` + `frontend/src/hooks/useTreeGraphs.ts:40-47`**
  The canvas area renders a `"Loading tree…"` placeholder whenever
  `graph` (i.e. `graphs.activeGraph`) is `undefined` — which is true both
  while a fetch is genuinely in flight *and* after that fetch has permanently
  failed (the `.catch` at `useTreeGraphs.ts:45` only sets a separate `error`
  string; it never marks the tree as "failed" or clears the loading
  placeholder). On a backend-down scenario or a 404 for the initially-selected
  tree, the user is stuck looking at "Loading tree…" indefinitely, with only a
  small dismissable-looking error banner elsewhere on the page and no retry
  button. (Switching tabs away and back does retry the fetch, since
  `graphCache[activeTreeKey]` is still empty on failure — but nothing in the
  UI suggests that's the recovery path.)
  Suggested fix direction: track a per-tree load status (`'loading' |
  'error' | 'loaded'`) instead of inferring it from cache-miss, and surface a
  retry action in the empty-state placeholder itself.

- **Severity: Low — `frontend/src/dashboard/PatientsPanel.tsx`**
  `loading` state is tracked and does correctly suppress a premature "No
  patients match this search" flash (line 120: `!loading` gate), but no
  spinner/"Searching…" text is ever rendered — while a search is in flight the
  panel just keeps showing the previous result set (or nothing, on first
  load) with no visual indication a request is running.

- Loading/empty/error states elsewhere are handled correctly:
  `dashboard/DashboardPage.tsx:85-87` (explicit empty-cohort hero message),
  `dashboard/PatientDetailModal.tsx:52` ("Loading patient…"), and
  `panels/TraversalResultModal.tsx:97` (`if (!props.result && !props.partial)
  return null` — modal simply doesn't render rather than rendering against
  undefined data).

---

## Summary

| Category | Critical | High | Medium | Low | Needs confirmation |
|---|---|---|---|---|---|
| 1. React state management | 0 | 0 | 0 | 2 | 0 |
| 2. useEffect correctness / memory leaks | 0 | 0 | 2 | 0 | 0 |
| 3. Race conditions | 0 | 0 | 1 | 0 | 2 |
| 4. Re-render loops / performance | 0 | 0 | 1 | 0 | 0 |
| 5. Out-of-bounds / undefined access | 0 | 1 | 0 | 1 | 0 |
| 6. Unhandled errors and validation | 1 | 0 | 1 | 0 | 1 |
| 7. Async / loading state | 0 | 0 | 1 | 1 | 0 |
| **Total** | **1** | **1** | **6** | **4** | **3** |

Note: the High item in §5 (no runtime response validation) and the Critical
item in §6 (no error boundary) are two halves of the same underlying risk —
unvalidated backend data crashing an unprotected render tree — and are cheap
to address together (add a boundary; optionally add a light shape-check on
the tree-graph response specifically, since that's the highest-traffic
unvalidated payload).

### Genuine bugs vs. robustness suggestions

**Genuine bugs / concrete defects:**
- No error boundary anywhere (§6, Critical)
- `PatientsPanel` search race — stale results can overwrite fresher ones (§3, Medium)
- `PatientsPanel` fetch not cancelled/guarded on unmount (§2, Medium)
- `App.tsx` new-`Set`-per-render defeats `useTreeCanvasSync`'s highlight-diff effect during sidebar resize (§4, Medium)
- `DonutStat` divide-by-zero → `NaN%` (§5, Low)
- Dead `rateVerdict(...)` call with discarded result (§1, Low)

**Robustness / design-smell suggestions (not bugs per se):**
- No runtime schema validation of any API response (§5/§6)
- Non-JSON error bodies produce ugly parse-error messages instead of friendly ones (§6)
- "Loading tree…" indistinguishable from "failed to load" (§7)
- No visible loading indicator in `PatientsPanel` (§7)
- `handleChangeArrowKind` / `handleResetLayout` ref-consistency and DELETE/PUT ordering nuances (§3, Needs confirmation)
- Dashboard keeps rendering stale `summary` alongside a fetch error (§6, Needs confirmation)
