# Mobile Responsive Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the decision-tree workbench, dashboard, and showcase usable on phone-sized screens while preserving the current desktop experience.

**Architecture:** Keep the existing desktop DOM and CSS layout. Add a small media-query hook and mobile-only drawer coordination to `TreeWorkspace`; use CSS media queries for workbench positioning and for dashboard/showcase reflow. Add source-boundary tests for the CSS contracts because jsdom does not calculate layout, and component tests for drawer state because that behavior is interactive.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, CSS media queries, lucide-react.

## Global Constraints

- Preserve the existing uncommitted frontend changes; only add or modify files listed in each task.
- Keep clinical branching, API contracts, tree data, and saved graph layouts unchanged.
- Use `780px` for workbench/showcase structural changes, `760px` for dashboard grid collapse, and `640px` for compact dashboard controls.
- Use a workbench drawer width of `min(88vw, 340px)` on mobile.
- Keep desktop resizers, fixed side-panel behavior, theme behavior, and existing content unchanged.
- Follow test-driven development: write each failing test or source-boundary assertion, run it, then implement the smallest change that makes it pass.
- Do not add a new dependency.

---

### Task 1: Add testable mobile drawer state to the workbench

**Files:**
- Create: `frontend/src/hooks/useMediaQuery.ts`
- Create: `frontend/src/app/TreeWorkspace.test.tsx`
- Modify: `frontend/src/app/TreeWorkspace.tsx:1-115`

**Interfaces:**
- `useMediaQuery(query: string): boolean` returns the current `window.matchMedia(query).matches` value and updates when the media query changes.
- `TreeWorkspace` keeps its existing props and desktop panel behavior. On mobile, its internal drawer state is `MobileDrawer = 'patient' | 'details' | null`.

- [ ] **Step 1: Write the failing media-query and drawer tests**

Create a jsdom test that stubs `window.matchMedia`, mocks the canvas and panel children, and renders `TreeWorkspace` with `graph={undefined}` so the test does not load tldraw. Use `ComponentProps<typeof TreeWorkspace>` for the fixture so the fixture stays aligned with the component contract.

The core assertions should be split into independent tests:

```tsx
it('opens the patient drawer and exposes its expanded state on mobile', async () => {
  const user = userEvent.setup()
  render(<TreeWorkspace {...mobileProps} />)

  await user.click(screen.getByRole('button', { name: 'Show patient panel' }))

  expect(screen.getByRole('button', { name: 'Hide patient panel' }))
    .toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByRole('button', { name: 'Close open panel' })).toBeInTheDocument()
})

it('keeps only one mobile drawer open at a time', async () => {
  const user = userEvent.setup()
  render(<TreeWorkspace {...mobileProps} />)

  await user.click(screen.getByRole('button', { name: 'Show patient panel' }))
  await user.click(screen.getByRole('button', { name: 'Show details panel' }))

  expect(screen.getByRole('button', { name: 'Show patient panel' }))
    .toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByRole('button', { name: 'Hide details panel' }))
    .toHaveAttribute('aria-expanded', 'true')
})

it('closes the active mobile drawer from the backdrop', async () => {
  const user = userEvent.setup()
  render(<TreeWorkspace {...mobileProps} />)

  await user.click(screen.getByRole('button', { name: 'Show patient panel' }))
  await user.click(screen.getByRole('button', { name: 'Close open panel' }))

  expect(screen.getByRole('button', { name: 'Show patient panel' }))
    .toHaveAttribute('aria-expanded', 'false')
})
```

Use a `matchMedia` result with `matches: true`, `addEventListener`, and
`removeEventListener` methods. Mock `MockPatientSidebar`, `Legend`,
`NodeDetailPanel`, `GlobalConfigPanel`, and `TreeCanvas` to simple elements so
these tests exercise only `TreeWorkspace` state and accessible controls.

- [ ] **Step 2: Run the focused tests and verify they fail for the missing behavior**

Run:

```bash
pnpm --dir frontend exec vitest run src/app/TreeWorkspace.test.tsx
```

Expected: FAIL because `TreeWorkspace` has no mobile media-query state,
backdrop, or mutually exclusive drawer behavior yet. If the test errors while
loading the fixture, fix only the test mocks or fixture until it fails on the
missing behavior.

- [ ] **Step 3: Implement the media-query hook and mobile state**

Implement `useMediaQuery` with an initial `matchMedia` read, a `change` event
subscription, and cleanup. Include the `addListener`/`removeListener` fallback
for browsers that expose the older MediaQueryList API.

In `TreeWorkspace`, add:

```tsx
const MOBILE_LAYOUT_QUERY = '(max-width: 780px)'
type MobileDrawer = 'patient' | 'details' | null

const isMobile = useMediaQuery(MOBILE_LAYOUT_QUERY)
const [mobileDrawer, setMobileDrawer] = useState<MobileDrawer>(null)

const toggleMobileDrawer = (drawer: Exclude<MobileDrawer, null>) => {
  setMobileDrawer((current) => (current === drawer ? null : drawer))
}
```

Use the existing collapse handlers for desktop and the mobile drawer handler
when `isMobile` is true. The left toggle must report
`isMobile ? mobileDrawer === 'patient' : !leftCollapsed` through
`aria-expanded`; the right toggle must use the equivalent `details` value.
Add `mobile-drawer-open` to the matching panel and render this close action
when a mobile drawer is active:

```tsx
{isMobile && mobileDrawer !== null && (
  <button
    type="button"
    className="mobile-drawer-backdrop"
    aria-label="Close open panel"
    onClick={() => setMobileDrawer(null)}
  />
)}
```

Clear `mobileDrawer` when the media query changes back to desktop. Do not
change the `leftCollapsed` or `rightCollapsed` semantics used by desktop.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```bash
pnpm --dir frontend exec vitest run src/app/TreeWorkspace.test.tsx
```

Expected: PASS for all drawer-state tests.

- [ ] **Step 5: Commit the workbench interaction unit**

```bash
git add frontend/src/hooks/useMediaQuery.ts frontend/src/app/TreeWorkspace.tsx frontend/src/app/TreeWorkspace.test.tsx
git commit -m "feat: coordinate mobile workbench drawers"
```

### Task 2: Add the mobile workbench drawer presentation

**Files:**
- Create: `frontend/tests/architecture/responsiveBoundaries.test.ts`
- Modify: `frontend/src/styles/panel-collapse.css:5-47`
- Modify: `frontend/src/styles/app-shell.css:20-115`
- Modify: `frontend/src/styles/canvas.css:5-109`

**Interfaces:**
- The React classes from Task 1 are the CSS contract: `.mobile-drawer-open`, `.mobile-drawer-backdrop`, `.panel-toggle-left.mobile-open`, and `.panel-toggle-right.mobile-open`.
- The workbench stays a full-height `.app-body`; only the mobile media query changes panel positioning.

- [ ] **Step 1: Write failing source-boundary tests for the workbench CSS contract**

Add architecture assertions that read the three CSS files with `readFileSync`
and verify the mobile contract before adding its rules:

```ts
it('defines the mobile workbench drawer contract', () => {
  const collapse = read('src/styles/panel-collapse.css')
  const shell = read('src/styles/app-shell.css')

  expect(collapse).toContain('@media (max-width: 780px)')
  expect(collapse).toContain('.mobile-drawer-open')
  expect(collapse).toContain('.mobile-drawer-backdrop')
  expect(collapse).toContain('.sidebar-resizer')
  expect(shell).toContain('.top-tabs-bar')
})
```

Also assert that the mobile workbench contract is included by `App.css` so a
future stylesheet split cannot silently remove the rules from the workbench.

- [ ] **Step 2: Run the architecture test and verify the expected failure**

Run:

```bash
pnpm --dir frontend exec vitest run tests/architecture/responsiveBoundaries.test.ts
```

Expected: FAIL on the missing mobile drawer selectors.

- [ ] **Step 3: Add mobile drawer positioning and touch sizing**

In the mobile media query, make `.app-body` clip the canvas viewport, hide the
desktop resizer, and position both panels as off-canvas overlays:

```css
@media (max-width: 780px) {
  .app-body { overflow: hidden; }

  .left-panel,
  .side-panels {
    position: absolute;
    top: 0;
    bottom: 0;
    z-index: 50;
    width: min(88vw, 340px) !important;
    transition: transform .2s ease;
  }

  .left-panel { left: 0; transform: translateX(-100%); }
  .left-panel.mobile-drawer-open { transform: translateX(0); }
  .side-panels { right: 0; transform: translateX(100%); }
  .side-panels.mobile-drawer-open { transform: translateX(0); }

  .sidebar-resizer { display: none; }
  .mobile-drawer-backdrop {
    position: absolute;
    inset: 0;
    z-index: 40;
    border: 0;
    background: rgba(0, 0, 0, .42);
  }
}
```

Override the existing inline toggle positions inside the mobile query so the
closed toggles sit 14px from their edge and the open toggle sits on the
drawer edge. Give both toggles a 44px hit area. Restore panel padding and
scrolling for a right drawer even when its desktop inline style is collapsed.

Keep the desktop rules untouched outside the mobile query. Add a reduced-motion
override that removes drawer and toggle transitions. Keep the tab bar
horizontally scrollable, reduce its mobile padding, and give `.top-tab` and
`.tab-scroll-btn` practical touch-sized heights. On narrow screens, constrain
the canvas toolbar to the viewport and allow its controls to scroll
horizontally rather than widening `.canvas-area`.

- [ ] **Step 4: Run the workbench architecture and component tests**

Run:

```bash
pnpm --dir frontend exec vitest run tests/architecture/responsiveBoundaries.test.ts src/app/TreeWorkspace.test.tsx
```

Expected: PASS with the new CSS contract and drawer behavior.

- [ ] **Step 5: Commit the workbench responsive presentation**

```bash
git add frontend/tests/architecture/responsiveBoundaries.test.ts frontend/src/styles/panel-collapse.css frontend/src/styles/app-shell.css frontend/src/styles/canvas.css
git commit -m "feat: make workbench panels responsive"
```

### Task 3: Reflow the dashboard for narrow screens

**Files:**
- Modify: `frontend/src/dashboard/styles/shell.css:1-110`
- Modify: `frontend/src/dashboard/styles/filters.css:3-44`
- Modify: `frontend/src/dashboard/styles/metrics.css:1-183`
- Modify: `frontend/src/dashboard/styles/patient-search.css:3-79`
- Modify: `frontend/src/dashboard/styles/patient-detail.css:1-60`
- Modify: `frontend/src/dashboard/styles/tables-and-tooltips.css:1-140`
- Modify: `frontend/src/styles/result-modal-shell.css:5-160`
- Modify: `frontend/tests/architecture/responsiveBoundaries.test.ts`

**Interfaces:**
- Dashboard markup and data components remain unchanged.
- Existing `.dash-grid`, `.dash-kpi-row`, `.dash-filters-grid`, `.dash-table-wrap`, `.modal-box`, and `.modal-body` classes are the styling boundaries.

- [ ] **Step 1: Extend the source-boundary test with failing dashboard assertions**

Add assertions for the required narrow-screen rules:

```ts
it('defines dashboard narrow-screen reflow contracts', () => {
  const shell = read('src/dashboard/styles/shell.css')
  const metrics = read('src/dashboard/styles/metrics.css')
  const filters = read('src/dashboard/styles/filters.css')
  const tables = read('src/dashboard/styles/tables-and-tooltips.css')
  const modal = read('src/styles/result-modal-shell.css')

  expect(shell).toContain('@media (max-width: 640px)')
  expect(metrics).toContain('.dash-card-wide')
  expect(metrics).toContain('grid-template-columns: minmax(0, 1fr)')
  expect(filters).toContain('.dash-filters-grid')
  expect(tables).toContain('.dash-table-wrap')
  expect(tables).toContain('min-width: max-content')
  expect(modal).toContain('max-width: calc(100vw - 16px)')
})
```

- [ ] **Step 2: Run the dashboard architecture test and verify it fails**

Run:

```bash
pnpm --dir frontend exec vitest run tests/architecture/responsiveBoundaries.test.ts
```

Expected: FAIL on the missing dashboard mobile assertions.

- [ ] **Step 3: Implement dashboard grid, filter, table, chart, and modal rules**

At `max-width: 760px`, make `.dash-grid`, `.dash-kpi-row`, and
`.dash-efficacy-row` use `grid-template-columns: minmax(0, 1fr)`, make
`.dash-card` `min-width: 0`, and keep `.dash-card-wide` in one column. At
`max-width: 640px`, set dashboard padding to `14px 12px 28px`, stack the
header/action controls, and set dashboard filter inputs/selects to
`width: 100%` and `min-width: 0`.

Make `.dash-filters-actions` fill available width without causing a second
scroll axis, keep search controls at `min-width: 0`, and allow chart legends
to wrap. Give `.dash-table` a mobile-only `min-width: max-content` so its
existing `.dash-table-wrap { overflow-x: auto; }` becomes the local horizontal
scroll region. Keep the dashboard page itself vertically scrollable.

At `max-width: 640px`, constrain the shared result modal with
`max-width: calc(100vw - 16px)` and `max-height: calc(100dvh - 16px)`, switch
the four-stat row to two columns, reduce modal padding, and ensure the modal
body remains the only vertical scroll region. Do not change modal content or
the existing result-modal-specific `680px` stacking rules.

- [ ] **Step 4: Run dashboard-related tests and the architecture test**

Run:

```bash
pnpm --dir frontend exec vitest run tests/architecture/responsiveBoundaries.test.ts src/dashboard
```

Expected: PASS. The dashboard component tests should continue to verify data
and interactions while the source test verifies the CSS contract.

- [ ] **Step 5: Commit the dashboard responsive unit**

```bash
git add frontend/src/dashboard/styles frontend/src/styles/result-modal-shell.css frontend/tests/architecture/responsiveBoundaries.test.ts
git commit -m "feat: reflow dashboard for mobile"
```

### Task 4: Harden the showcase phone layout

**Files:**
- Modify: `frontend/src/showcase/showcase-layout.css:1-174`
- Modify: `frontend/src/showcase/showcase-scroll.css:1-29`
- Modify: `frontend/src/showcase/showcase-chart.css:1-230`
- Modify: `frontend/src/showcase/showcase-focus.css:1-105`
- Modify: `frontend/src/showcase/showcase-empty.css:1-30`
- Modify: `frontend/src/showcase/showcase-modal.css:1-5`
- Modify: `frontend/tests/architecture/responsiveBoundaries.test.ts`

**Interfaces:**
- Keep `ShowcasePage`, `ShowcaseChrome`, `PatientQueue`, and `PatientChart` markup and behavior unchanged.
- Existing showcase variables, typography, theme selectors, and modal classes remain the visual system.

- [ ] **Step 1: Extend the source-boundary test with failing showcase assertions**

Add assertions for the existing and strengthened phone layout:

```ts
it('defines showcase phone layout contracts', () => {
  const layout = read('src/showcase/showcase-layout.css')
  const scroll = read('src/showcase/showcase-scroll.css')
  const modal = read('src/showcase/showcase-modal.css')

  expect(layout).toContain('@media (max-width:780px)')
  expect(layout).toContain('.sc-patient-card')
  expect(layout).toContain('.sc-chart-layout')
  expect(scroll).toContain('@media (min-width: 781px)')
  expect(scroll).toContain('overscroll-behavior-x: contain')
  expect(modal).toContain('max-width: calc(100vw - 16px)')
})
```

- [ ] **Step 2: Run the architecture test and verify the new assertion fails**

Run:

```bash
pnpm --dir frontend exec vitest run tests/architecture/responsiveBoundaries.test.ts
```

Expected: FAIL on the new selector or overflow contract added for the
showcase phone rules.

- [ ] **Step 3: Implement the showcase narrow-screen safeguards**

Keep the current `780px` grid, horizontal patient queue, and single-column
chart rules, then add the safeguards needed at phone widths:

- Apply `min-width: 0` to the grid children and chart identity so long patient
  names, labels, and chart content cannot widen the page.
- Keep `.sc-queue-list` horizontally scrollable with
  `overscroll-behavior-x: contain`; keep cards touch-sized and prevent hover
  transforms on touch layouts.
- At very narrow widths, stack the vital band to one column and stack the
  follow-up data fields, adding borders between rows instead of relying on
  horizontal space.
- Let the topbar controls shrink or hide only the already nonessential
  context/avatar text; keep the clinic mark and theme/notification actions
  reachable.
- Cap showcase result modal width to the viewport and keep its body vertically
  scrollable, using the shared modal rules without changing content.
- Add a reduced-motion rule for any new mobile transitions.

- [ ] **Step 4: Run showcase tests and the architecture test**

Run:

```bash
pnpm --dir frontend exec vitest run tests/architecture/responsiveBoundaries.test.ts src/showcase
```

Expected: PASS, including the existing showcase theme and evaluation tests.

- [ ] **Step 5: Commit the showcase responsive unit**

```bash
git add frontend/src/showcase frontend/tests/architecture/responsiveBoundaries.test.ts
git commit -m "feat: harden showcase mobile layout"
```

### Task 5: Run the full frontend verification and review the change boundary

**Files:**
- Modify: none unless a verification failure identifies a regression in the files listed above.

**Interfaces:**
- All previous tasks produce a buildable frontend with unchanged API and clinical behavior.

- [ ] **Step 1: Run the full frontend test suite**

Run:

```bash
pnpm --dir frontend test
```

Expected: all Vitest tests pass with no unhandled errors or warnings.

- [ ] **Step 2: Run the TypeScript/Vite production build**

Run:

```bash
pnpm --dir frontend build
```

Expected: `tsc -b` and `vite build` complete successfully.

- [ ] **Step 3: Run the frontend lint check**

Run:

```bash
pnpm --dir frontend lint
```

Expected: oxlint exits successfully.

- [ ] **Step 4: Check formatting and the user-change boundary**

Run:

```bash
git diff --check
git status --short
git diff --stat
```

Expected: no whitespace errors; the responsive commits contain only the
planned files, and the pre-existing user changes remain separate and are not
reformatted or reverted.

- [ ] **Step 5: Review the verified change boundary and hand off**

After all checks pass, report the exact test, build, and lint commands, the
responsive files changed, and any manual viewport checks still available to
the developer. If a check fails, return to the affected task's failing-test
step, make the smallest fix in that task's named files, rerun the check, and
commit that focused fix before handing off.
