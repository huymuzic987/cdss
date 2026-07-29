# Frontend

The visualizer is a Vite + React + TypeScript app in `frontend/`, using
[tldraw](https://tldraw.dev/) as the canvas engine for rendering decision
trees and [Recharts](https://recharts.org/) for the statistics dashboard.
There is no client-side router (no react-router or similar) and no
data-fetching library (no react-query/SWR) - navigation is local component
state, and all backend calls are plain `fetch()`.

This document describes the current structure. `frontend/README.md` predates
a refactor that split several large ("god-file") components into smaller
pieces - where the two disagree, this document and the code are correct;
see §6 for the specific points where `frontend/README.md` is stale.

## Dependencies and scripts

React 19.2, TypeScript, Vite 8, tldraw 5.1, `elkjs` 0.11 (automatic graph
layout), Recharts 3.10, `lucide-react` (icons). Linted with `oxlint`, not
ESLint. Package manager is `pnpm` (`pnpm-lock.yaml` is committed).

```bash
pnpm install
pnpm dev       # vite dev server
pnpm build     # tsc -b && vite build
pnpm lint      # oxlint
pnpm preview   # preview a production build locally
```

## How it talks to the backend

`frontend/src/api/client.ts` sets `API_BASE_URL = ''` - every call is a
relative path like `fetch('/trees')`. There is no configurable base URL
(despite what `frontend/README.md` currently implies - see §6); this works
because:

- In development, `vite.config.ts` proxies specific path prefixes
  (`/trees`, `/evaluate`, `/fhir`, `/health`, `/dashboard`) to
  `http://localhost:8000`.
- In production, `frontend/nginx.conf` proxies the same prefixes to the
  `backend` container - see [docs/deployment.md](deployment.md).

If you add a new backend route the frontend needs to call, it must be added
to **both** places or it will 404 in one environment.

`api/client.ts` exports one function per endpoint it uses:
`fetchTrees`, `fetchTreeGraph`, `fetchTreeLayout`, `saveTreeLayout`,
`resetTreeLayout`, `evaluateTree`, `fetchDashboardSummary`, `fetchPatients`,
`fetchPatientDetail`, `seedDashboardData`, `fhirPatientExportUrl` - see
[docs/api.md](api.md) for what each backend call actually returns.
`evaluateTree` has one special case: on an HTTP 424 (unresolved `LINK`) it
returns the partial result instead of throwing, so the canvas can still
visualize how far a traversal got before failing.

`api/types.ts` hand-mirrors the backend's Pydantic schemas
(`src/cdss/api/schemas/tree_graph.py`, `dashboard.py`, and the evaluation
response shape) as TypeScript interfaces. There is no code generation from
the OpenAPI schema - if a backend schema changes, `api/types.ts` has to be
updated by hand to match.

Two environment variables are used, both unrelated to the API base URL:
`VITE_TLDRAW_LICENSE_KEY` (must be set at build time - see
[docs/deployment.md](deployment.md)) and `VITE_PRODUCTION` (toggles the
traversal-result modal between a clinical-only summary and a full debug/audit
view - see §4).

## `main.tsx` / `App.tsx`

`main.tsx` renders a single component, `<App />`, in `<StrictMode>` - no
router. `App.tsx` (~300 lines) owns nearly all top-level state:

- **Theme**: persisted to `localStorage`, applied as
  `document.documentElement.dataset.theme`.
- **View toggle**: a boolean `showDashboard` switches the entire body between
  the tree-canvas view and `<DashboardPage />`. This is the app's only
  "routing," and it's local component state, not a URL.
- **Tree tabs**: one tab per seeded tree (via `useTreeGraphs`, see below),
  filtered down to only the trees a traversal has actually touched once one
  is running, plus a `Dashboard` tab.
- **Modals**: `<TraversalResultModal>` and `<DrugToleranceCheckbox>` (a
  mid-traversal popup - see §4) are rendered at the root, controlled by
  state from `useTraversal`.

```text
App
├── top tab bar (Dashboard + one tab per touched tree)
├── [showDashboard]
│    └── DashboardPage  (see §5)
└── [!showDashboard]
     ├── MockPatientSidebar   (left panel - builds the /evaluate request)
     ├── TreeCanvas           (center - the tldraw graph, see §3)
     ├── Legend / NodeDetailPanel / GlobalConfigPanel  (right panels)
     ├── TraversalResultModal (conditional)
     └── DrugToleranceCheckbox (conditional)
```

## Hooks (`src/hooks/`)

Three hooks, each composed directly in `App.tsx`:

- **`useTreeGraphs`**: fetches the tree list, manages the tab/active-tree
  state, and lazily caches each tree's graph after first fetch (so
  switching tabs back and forth doesn't re-fetch). Also resolves
  cross-tree `LINK` navigation (jumping to another tree's tab and
  highlighting the target node).
- **`useTraversal`** (~420 lines, the largest hook) - drives `/evaluate`
  calls, tracks which nodes are highlighted/active per tree during and after
  a run, supports both "auto-run" (show the final result immediately) and
  "manual step-through" (advance one trace entry per click, via
  `useManualModeClicks` in the canvas layer) modes, and owns the
  drug-tolerance mid-traversal pause described in §4.
- **`useSidebarResize`**: drag-to-resize for the right-hand panel group
  (240–600px).

## The canvas (`src/canvas/`)

The tldraw-based tree visualizer, split into 8 focused files (this is the
part of the frontend that most recently went through the "god-file" split -
`frontend/README.md` still describes only 3 of them):

- **`TreeCanvas.tsx`**: the host component. Composes the hooks below,
  renders the custom toolbar (search, fit-to-view, arrow-style toggle,
  reset-layout) and the `<Tldraw>` element itself, configured with a single
  custom shape (`SHAPE_UTILS=[DecisionNodeShapeUtil]`) and most of tldraw's
  stock UI chrome hidden.
- **`DecisionNodeShapeUtil.tsx`**: the custom `decisionNode` shape: a
  non-resizable, non-editable flowchart card colored per `NodeType`
  (`START`/`CONDITION`/`INFERENCE`/`ACTION`/`END`/`LINK`/`GLOBAL`), with its
  own highlight states (`none`/`entered`/`active`) and a `dimmed` variant
  used during traversal playback. There is no custom tldraw *tool* - nodes
  are only ever generated from graph data, never hand-drawn.
- **`buildTreeScene.ts`**: pure function: `TreeGraphNode[]`/
  `TreeGraphEdge[]` + a positions map → tldraw shapes and arrow bindings.
  Edges are native tldraw `arrow` shapes bound to the two `decisionNode`
  shapes at each end, tagged with `meta.edgeKey = "{from}->{to}"` so saved
  layout can be matched back to a graph edge independent of tldraw's own
  (regenerated) shape ids.
- **`edgeLayout.ts`**: reads current arrow geometry back out of the live
  tldraw store, keyed the same way, for saving.
- **`useTreeCanvasScene.ts`**: the mount/sync core: on mount, runs the ELK
  auto-layout (`layout/elkLayout.ts`) and fetches the saved backend layout
  in parallel; any node with a saved position uses it, everything else falls
  back to the ELK-computed position; builds the scene; then listens to the
  tldraw store for user edits (drag, arrow-kind change) and debounce-saves
  (800ms) back to `PUT /trees/{tree_key}/layout`, flushing immediately on
  unmount so a fast tab switch doesn't drop the last drag.
- **`useTreeCanvasControls.ts`**: the toolbar's behaviors: search/zoom-to a
  node, toggle arrow kind (persisted), and "reset layout"
  (`DELETE /trees/{tree_key}/layout` then recompute pure ELK positions).
- **`useTreeCanvasSync.ts`**: keeps the mounted scene in sync with
  reactive props: color scheme following app theme, pan/select on
  `focusNodeKey` change, per-node highlight/dim state during traversal
  playback, and camera pan/center onto the currently active traversal node.
- **`useManualModeClicks.ts`**: during manual step-through mode,
  distinguishes a plain click from a drag (5px threshold) so a click on the
  canvas (not on the toolbar, not modified) advances one trace step.

`layout/elkLayout.ts` is the one file outside `canvas/` this depends on: it
wraps `elkjs` (layered, top-down, network-simplex placement) and exports the
fixed node box size (`NODE_WIDTH=220`, `NODE_HEIGHT=72`) both the initial
layout and the reset button use.

## Traversal UI (`src/panels/`)

- **`MockPatientSidebar.tsx`**: the left "Patient Simulator" panel. Composes
  four form sections from `panels/mockPatientForm/`
  (`DemographicsSection`, `BloodPressureSection`, `CareSettingSection`,
  `ComorbiditiesSection`), a preset picker backed by `patientPresets.ts`
  (~700 lines of canned scenarios grouped by category - diagnosis routes,
  demographic/comorbidity diversity, follow-up visits, modifier/complication
  trees, pregnancy/postpartum), and client-side validation. On submit, it
  converts form state to the engine's flat input shape
  (`mockPatientForm/payload.ts`) and then to a FHIR R4 `Bundle`
  (`mockPatientForm/fhirBundle.ts`) - this file is a deliberate, explicit
  frontend port of the backend's `bundle_to_input`/`input_to_bundle` mapping
  in `src/cdss/api/schemas/fhir_input.py` (see [docs/api.md](api.md#12-the-input-bundle-contract)).
  Keep the two in sync if either side's field mapping changes.
- **`TraversalResultModal.tsx`** (~470 lines) - renders a completed or
  partial (424) `/evaluate` result: a human-readable decision summary,
  recommended actions/medicines (reading `medicine_options`/`medicines` off
  the action payload - see [docs/cdss/json-dialect.md](cdss/json-dialect.md)
  §8.1), and a collapsible debug section. What's shown by default differs by
  `import.meta.env.VITE_PRODUCTION === '1'`: a clinical-only summary in
  production builds, or the full traversal log / candidate-condition detail
  otherwise.
- **`DrugToleranceCheckbox.tsx`**: a modal that pauses traversal mid-run on
  the resistant-hypertension pathway (triggered at node key
  `T13_A_CHECK_MRA`), asks whether the patient tolerates
  MRA/spironolactone, patches that answer into the FHIR bundle input, and
  re-evaluates. This is the one place the frontend has hardcoded knowledge
  of a specific node key from a specific tree - a reminder that a decision
  tree's node keys are effectively part of its interface if any UI needs to
  react to reaching one mid-run.
- **`NodeDetailPanel.tsx`**: selected-node inspector: bilingual text, raw
  JSON for `condition_definition`/`context_patch`/`action_payload`, a jump
  button for `LINK` nodes, and source references.
- **`GlobalConfigPanel.tsx`**: renders a tree's `GLOBAL` node configs.
- **`Legend.tsx`**: the seven-`NodeType` color key, reusing the canvas's own
  color function.
- **`CopyButton.tsx`**: shared clipboard-copy control.
- **`TreeNavigator.tsx`**: a categorized/searchable tree-picker component
  that exists in the codebase but is **not imported anywhere**: the top tab
  bar in `App.tsx` is what actually drives tree selection today. Left as-is
  per this project's "surgical changes" convention (not deleted as part of
  this documentation pass); worth knowing about if you're looking for where
  tree selection happens and land here first.

## Dashboard (`src/dashboard/`)

A self-contained analytics view, entirely separate data path from the tree
canvas - every component here reads only `/dashboard/*` endpoints (see
[docs/api.md](api.md#5-statistics-dashboard-dashboard)).

- **`DashboardPage.tsx`** (~600 lines) - top-level: fetches
  `/dashboard/summary` with the current filter set, composes
  `FiltersBar`, `SeedControls`, KPI `StatTile`s, and several `SectionCard`s
  wrapping `BarStat`/`LineStat`/`DonutStat`/`DataTable`
  (`dashboard/charts/`), plus `PatientsPanel` and `PatientDetailModal`.
- **`FiltersBar.tsx`**: department/age/gender/comorbidity/adherence filter
  form with local draft state and quick-filter chips; this cohort filter is
  independent of `PatientsPanel`'s own search box.
- **`SeedControls.tsx`**: buttons that call `POST /dashboard/seed` for each
  of the three sources (`preset`/`synthetic`/`real_test_case` - see
  [docs/operations.md](operations.md)), plus a link to the FHIR patient
  export.
- **`PatientsPanel.tsx`** / **`PatientDetailModal.tsx`**: debounced
  (300ms) patient search/pagination and a single-patient detail view with a
  BP trend chart.
- **`chartColors.ts`** / **`charts/*.tsx`**: the dashboard's color system
  (CSS-custom-property-backed, validated for both light and dark themes) and
  Recharts wrapper components sharing one visual style.
- **`humanize.ts`**, **`explanations.ts`**, **`verdict.ts`**, **`csv.ts`** -
  small focused utilities: enum/code → label lookups, plain-language stat
  tooltips, rate → status-color mapping, and client-side CSV export.

`frontend/README.md` does not mention this directory at all - see §6.

## What's stale in `frontend/README.md`

If you're reading `frontend/README.md` alongside this document, treat this
document and the current code as authoritative on these specific points:

1. Its `canvas/` file list names only 3 files; the folder now has 8 (see
   §3) - the scene-mount/layout-save/sync logic it attributes loosely to
   `TreeCanvas.tsx` now lives in four extracted hooks.
2. It does not mention `src/dashboard/` at all, even though it's the
   largest subsystem in `src/` by file count.
3. Its `panels/` description omits `TreeNavigator.tsx`,
   `DrugToleranceCheckbox.tsx`, and the entire `mockPatientForm/`
   sub-folder that `MockPatientSidebar.tsx` was split into.
4. It says the API base URL is configurable ("You can configure a custom
   API endpoint in Vite settings if needed"). It isn't - see the "How it
   talks to the backend" section above; changing where the frontend talks to
   requires editing the Vite dev proxy or `nginx.conf`, not a setting.
