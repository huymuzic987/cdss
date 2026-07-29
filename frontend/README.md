# CDSS Frontend

A Vite, React, and TypeScript application containing:

- an interactive decision-tree visualizer built with tldraw;
- mock-patient evaluation and traversal playback;
- a clinical statistics dashboard built with Recharts.

## Run locally

The backend should already be running on port 8000.

~~~powershell
pnpm install
pnpm dev
~~~

Vite normally serves the application on http://localhost:5173 and proxies API
requests to the backend.

## Checks

~~~powershell
pnpm build
pnpm lint
~~~

## Component boundaries

- api contains fetch wrappers and TypeScript representations of backend data.
- canvas renders tree graphs and manages visual layout interactions.
- hooks coordinate application and traversal state.
- panels contain patient simulation, node inspection, and result presentation.
- dashboard contains reporting views and chart components.

The frontend may react to traversal results, but clinical branching belongs in
database-defined trees. Any UI dependency on a particular tree or node key is
an interface dependency and should be documented and tested.

The current composition facades are `App.tsx`, `hooks/useTraversal.ts`,
`panels/patientPresets.ts`, `mockPatientForm/fhirBundle.ts`, and the root CSS
entry files. Focused implementation lives under `app/`, `hooks/traversal/`,
`panels/patientPresets/`, `panels/clinicalPresentation/`,
`panels/clinicalResult/`, `dashboard/sections/`, and the style directories.

## Detailed guides

- [Frontend architecture](../docs/frontend.md)
- [API guide](../docs/api/README.md)
- [Tree graph and layout API](../docs/api/trees-and-layouts.md)
- [Clinical evaluation API](../docs/api/evaluation.md)
- [Deployment](../docs/deployment.md)
