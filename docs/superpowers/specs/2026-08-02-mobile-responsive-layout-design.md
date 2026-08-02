# Mobile Responsive Layout Design

## Context

The frontend contains three user-facing surfaces: the decision-tree workbench,
the clinical dashboard, and the showcase. The dashboard and showcase already
have partial narrow-screen rules, while the workbench currently assumes two
desktop side panels surrounding a full-height canvas.

The implementation must preserve the existing desktop layout and the user's
current uncommitted changes. Mobile support is a presentation and interaction
change; clinical branching, API contracts, tree data, and saved graph layouts
are out of scope.

## Goals

- Make every frontend surface usable at narrow phone widths without accidental
  horizontal page overflow.
- Keep the decision-tree canvas as the primary mobile workbench surface.
- Make the patient simulator and node-detail panels available as mobile drawers.
- Preserve the existing desktop resizable-panel experience.
- Maintain touch-friendly controls, readable text, keyboard focus, and the
  existing theme behavior.
- Keep wide data tables and chart content usable through local scrolling where
  collapsing would make the data unreadable.

## Responsive approach

Use a component-aware responsive shell combined with focused CSS media queries.
The React layer owns mobile drawer coordination because drawer visibility and
backdrop behavior are interaction state. CSS owns sizing, positioning, and
surface-specific reflow. No separate mobile markup tree is needed.

The existing narrow-screen boundaries remain the starting point:

- `780px` for workbench/showcase structural changes.
- `760px` for dashboard grid collapse.
- `640px` for compact dashboard spacing and controls.

The workbench should use a `max-width: 340px` drawer capped at approximately
`88vw`. On mobile, the patient and details drawers are mutually exclusive so
they cannot obscure each other. A backdrop closes the active drawer and keeps
the canvas interaction predictable. Desktop panel state and resizing remain
unchanged.

## Surface behavior

### Decision-tree workbench

- The app body remains a viewport-sized flex layout, with the canvas filling
  the available width and height.
- The left patient simulator becomes a left-side overlay drawer.
- The right legend/details/configuration panel becomes a right-side overlay
  drawer.
- Existing panel toggles remain the entry points and receive touch-sized hit
  areas on narrow screens.
- The drawer body scrolls independently; the page itself does not need to
  scroll while the workbench is active.
- The top tree tabs remain horizontally scrollable and do not wrap into extra
  rows.
- Desktop resizers, fixed panel widths, and canvas behavior are unchanged.

### Dashboard

- The dashboard owns vertical page scrolling on narrow screens.
- KPI and dashboard card grids collapse to one column.
- Header actions and filters wrap or stack to fit the viewport.
- Tables retain readable column sizing inside local horizontal scroll regions.
- Charts keep a usable minimum drawing area and avoid forcing the whole page
  wider than the viewport.
- Patient detail and related modal content fit within the viewport with
  scrollable internal content.

### Showcase

- Retain the existing compact navigation rail and horizontal patient queue.
- Keep chart content single-column at phone widths.
- Stack vital/follow-up data where the current two-column arrangement becomes
  too narrow.
- Tighten header, modal, and card spacing only where needed to prevent
  clipping or overflow.
- Do not change showcase content, visual identity, or interaction flow.

## Accessibility and interaction

- Drawer toggles expose accurate `aria-expanded` state and descriptive labels.
- The mobile backdrop is keyboard reachable only if it is represented as a
  close action; otherwise it remains decorative and the drawer toggle provides
  the accessible close path.
- Focus-visible styles remain visible against both themes.
- Interactive controls use at least a practical touch target near 44px where
  the mobile rules change their dimensions.
- Reduced-motion users do not receive drawer or tab animations that violate
  the existing reduced-motion conventions.

## Testing and verification

Add focused component coverage for the workbench drawer behavior: opening one
drawer closes the other, the backdrop is shown while a drawer is open, and the
accessible state reflects visibility. Existing dashboard/showcase tests remain
the regression boundary for those surfaces.

Because jsdom does not calculate media-query layout, CSS behavior will be
verified with static build/lint checks plus inspection of the responsive rules.
Run the frontend test suite, build, and lint after implementation.

## Acceptance criteria

- At phone widths, the workbench canvas is usable without page-level
  horizontal scrolling.
- Both workbench side panels can be opened and closed as drawers.
- Opening the second drawer closes the first and a visible backdrop closes the
  active drawer.
- Dashboard and showcase content remain readable and usable at phone widths.
- Desktop behavior remains equivalent to the current layout.
- Focused tests, full frontend tests, build, and lint pass.
