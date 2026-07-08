# Hypertension CDSS Frontend Visualizer

An interactive, canvas-based visualizer for clinical decision trees built with **React**, **TypeScript**, **Vite**, **tldraw**, and **elkjs**. It queries tree configurations from the backend FastAPI service and renders them dynamically on an infinite pan/zoom whiteboard canvas.

---

## 🏗️ Architecture & Component Design

The application code is located in the [src/](file:///c:/Users/Huy/Desktop/cdss/frontend/src) directory:

```text
src/
├── api/             # HTTP Client and type definitions for backend communication
├── canvas/          # Tldraw whiteboard wrapper and custom shapes
├── hooks/           # State/logic for tree data, traversal simulation, and sidebar resizing
├── layout/          # ELK automatic flowchart layout generator
├── panels/          # Inspector panels, mock-patient simulator, and visual legend components
├── App.tsx          # Main layout coordinator (composes the hooks and renders the layout)
├── App.css          # Core layouts and tab bar styles
├── index.css        # Global CSS variables and fonts
└── main.tsx         # React bootstrap mounting point
```

### 1. API Integration (`src/api`)
Handles all dynamic data communication with the FastAPI backend:
* **[api/client.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/api/client.ts)**: Implements asynchronous fetch queries (`fetchTrees`, `fetchTreeGraph`) targeting backend endpoints.
* **[api/types.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/api/types.ts)**: Matches Pydantic schemas, defining interfaces like `TreeSummary`, `TreeGraphNode`, and `TreeGraphResponse`.

### 2. Tldraw Canvas Engine (`src/canvas`)
Provides custom graphics and controls for rendering decision-tree flowcharts:
* **[canvas/TreeCanvas.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/canvas/TreeCanvas.tsx)**: Main tldraw canvas host. It registers custom shape utilities, handles selection events, and manages camera focus adjustments (zooming and panning to highlighted nodes).
* **[canvas/DecisionNodeShapeUtil.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/canvas/DecisionNodeShapeUtil.tsx)**: Custom HTML shape utility that renders flowchart cards. Nodes are colored and styled according to their clinical type (`START`, `CONDITION`, `INFERENCE`, `ACTION`, `END`, `LINK`).
* **[canvas/buildTreeScene.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/canvas/buildTreeScene.ts)**: Constructs the tldraw scene graph by creating nodes, connector lines (edges), and text labels from the layout coordinates.

### 3. Automated Layout (`src/layout`)
Flowchart layouts are generated dynamically rather than hardcoded in position:
* **[layout/elkLayout.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/layout/elkLayout.ts)**: Integrates **elkjs** (Eclipse Layout Kernel) to automatically calculate clean coordinates, branch arrangements, and connector routes.

### 4. Inspector Sidebar & Utilities (`src/panels`)
Presents detailed information about selected nodes and configurations:
* **[panels/NodeDetailPanel.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/panels/NodeDetailPanel.tsx)**: Sidebar inspector. It decodes and renders JSON condition definitions, context merge patches, action payloads, and clinical citation references. Includes interactive navigation to jump across decision trees when clicking cross-tree `LINK` node types.
* **[panels/GlobalConfigPanel.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/panels/GlobalConfigPanel.tsx)**: Shows tree-level configs extracted from `GLOBAL` nodes (such as age limits and risk weights).
* **[panels/MockPatientSidebar.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/panels/MockPatientSidebar.tsx)**: Form-driven mock-patient simulator. Collects clinic/home/ambulatory BP readings, demographics, and comorbidities into a `PatientFormData` shape, and lets developers load canned scenarios from `patientPresets.ts` before running a traversal via `useTraversal`.
* **[panels/patientPresets.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/panels/patientPresets.ts)**: Canned `PatientPreset` entries (diagnosis routes, demographic/comorbidity diversity, follow-up visits) used to prefill `MockPatientSidebar`.
* **[panels/TraversalResultModal.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/panels/TraversalResultModal.tsx)**: Renders the `/evaluate` result or partial-failure state as a step-by-step trace, showing each evaluated condition with a pass/fail/neutral badge.
* **[panels/CopyButton.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/panels/CopyButton.tsx)**: Small reusable clipboard-copy control used inside inspector panels.
* **[panels/Legend.tsx](file:///c:/Users/Huy/Desktop/cdss/frontend/src/panels/Legend.tsx)**: A visual guide explaining colors associated with each node type.

### 5. Application State (`src/hooks`)
`App.tsx` composes these hooks and renders the layout; each hook owns one concern:
* **[hooks/useTreeGraphs.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/hooks/useTreeGraphs.ts)**: Tree list/tab state, per-tree graph caching, and cross-tree link navigation.
* **[hooks/useTraversal.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/hooks/useTraversal.ts)**: Drives the mock-patient traversal simulation — calls `/evaluate`, preloads every graph the trace touches, tracks highlighted/active nodes, supports a manual step-through mode (reveal one `node_entered` trace entry per canvas click), and surfaces `TraversalResultModal`.
* **[hooks/useSidebarResize.ts](file:///c:/Users/Huy/Desktop/cdss/frontend/src/hooks/useSidebarResize.ts)**: Drag-to-resize behavior for the right-hand side panel.

---

## 🌟 Key Features

1. **Infinite Canvas Navigation**: Smooth zoom, drag, and pan interactions powered by the [tldraw](https://tldraw.dev/) whiteboard SDK.
2. **Automated Layered Layout**: Generates structured, readable tree flowcharts dynamically using [elkjs](https://github.com/kieler/elkjs).
3. **Interactive Link Navigation**: Enables developers to click a `LINK` node, immediately loading the target decision tree and centering the camera on the target node.
4. **Data Inspector**: Displays all clinical details (Vietnamese/English labels, operators, expression trees, context merge operations, and action recommendations) when a shape is clicked.
5. **Color-Coded Semantics**: Highlights node types using matching colors to differentiate conditions, inferences, and clinical outcomes.
6. **Mock-Patient Simulation**: A form-driven sidebar (with canned presets) runs a full clinical input through `/evaluate`, then walks the resulting trace step-by-step across the canvas, either animated or via manual click-through.

---

## 🛠️ Getting Started

### Prerequisites
* **Node.js 20+**
* **pnpm 10+** ( package manager )

### 1. Install Dependencies
Run package installation using pnpm:
```bash
pnpm install
```

### 2. Configure Development Env
By default, the client communicates with the backend on `http://localhost:8000`. You can configure a custom API endpoint in Vite settings if needed.

### 3. Run Development Server
```bash
pnpm dev
```
Open `http://localhost:5173` in your browser. (The backend FastAPI server must already be running on port 8000).

### 4. Linting and Verification
We use **oxlint** (an extremely fast linter written in Rust) and TypeScript compiler checks:
```bash
# Check compiler issues
pnpm build

# Run linter
pnpm lint
```
