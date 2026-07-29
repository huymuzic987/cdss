# Frontend Architecture

The frontend is a Vite, React, and TypeScript application with two major user
experiences: a decision-tree visualizer and a clinical statistics dashboard.

This guide describes stable responsibilities rather than listing every file.

## Runtime boundary

The browser calls relative API paths. Development proxy configuration and the
production web server forward those paths to the FastAPI backend.

When adding a frontend-consumed backend route, keep development and production
proxy configuration aligned. Frontend TypeScript types manually mirror backend
response schemas, so schema changes must be updated on both sides.

## Application shell

The application shell owns global presentation state such as theme, current
view, tree selection, and top-level dialogs. It composes the visualizer,
patient simulator, traversal results, and dashboard.

Global state should remain orchestration state. Feature-specific rendering and
data transformation belong with the feature that owns them.

## Decision-tree visualizer

The visualizer combines:

- tree-list and graph retrieval;
- automatic graph layout and persisted user layout;
- tldraw node and connector rendering;
- selected-node inspection and source references;
- cross-tree link navigation;
- traversal highlighting and playback.

Tree graph data and layout data are separate contracts. Clinical graph content
comes from tree definitions; saved layout contains presentation details such
as positions and connector choices.

See [Tree graphs and layouts](api/trees-and-layouts.md).

## Patient simulation and traversal

The simulator collects clinical inputs, validates them, and converts them into
the FHIR Bundle accepted by the backend. Traversal state then coordinates the
evaluation request, partial failures, visited trees, highlighted nodes, and
result presentation.

The frontend's FHIR conversion must remain compatible with the backend mapping.
See [Clinical evaluation](api/evaluation.md).

Clinical thresholds and branch decisions do not belong in form or presentation
components. If the UI must react to a particular tree or node key, treat that
key as an explicit interface dependency with a test.

## Dashboard

The dashboard is a reporting feature over persisted imported clinical data. It
owns filters, aggregate summaries, patient search, patient details, charts, and
exports.

This is a different data path from stateless tree evaluation:

~~~text
FHIR import or seed -> persisted visits -> dashboard queries -> charts

FHIR evaluation -> transient traversal -> recommendation and audit result
~~~

See [FHIR and dashboard API](api/fhir-and-dashboard.md).

## State ownership

Prefer state near the component or feature that owns it:

- API clients own transport and HTTP error interpretation.
- Feature hooks own asynchronous workflow and reusable feature state.
- Canvas modules own tldraw synchronization and layout interaction.
- Panels own form and presentation state.
- Dashboard modules own reporting filters and display transformations.

Derived values should be computed rather than duplicated across multiple state
owners.

## Verification

~~~powershell
pnpm --dir frontend build
pnpm --dir frontend lint
~~~

Run focused frontend tests for changed workflows when available. Changes to an
API schema, FHIR mapping, tree/node interface dependency, or saved layout
format require integration coverage at the boundary.

## Related guides

- [Frontend quickstart](../frontend/README.md)
- [API guide](api/README.md)
- [Backend components](components/backend.md)
- [Deployment](deployment.md)
