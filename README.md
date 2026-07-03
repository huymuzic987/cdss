# Hypertension Clinical Decision Support System (CDSS) Backend

A stateless, database-driven clinical decision-support API built with FastAPI, SQLAlchemy, and PostgreSQL. The clinical workflow is stored dynamically in the database as decision-tree nodes and edges, allowing a generic, stateless traversal engine to evaluate conditions, apply context patches, and collect actions without hardcoded branching in Python.

A companion Vite + React + tldraw decision-tree visualizer resides in the [frontend](file:///c:/Users/Huy/Desktop/cdss/frontend) directory.

---

## 🛠️ Technology Stack (What and Why)

The project leverages a modern, robust tech stack designed for speed, clinical accuracy, and stateless operation.

### Backend Core Stack
1. **[FastAPI](https://fastapi.tiangolo.com/)**
   * **What it does**: Handles the HTTP request/response cycle, routes evaluations, validates payloads using Pydantic, and generates interactive OpenAPI swagger docs.
   * **Why we use it**: It is extremely fast, fully supports type hints for automatic validation, and offers a stateless architecture ideal for high-throughput decision-support queries.
2. **[SQLAlchemy ORM](https://www.sqlalchemy.org/)**
   * **What it does**: Serves as the Object-Relational Mapper (ORM), translating Python classes into database tables/queries and providing session/transaction management.
   * **Why we use it**: It decouples the clinical traversal engine from raw SQL, facilitates clean database queries (such as the optimized 4-query graph loader), and handles transaction boundaries safely.
3. **[Alembic](https://alembic.sqlalchemy.org/)**
   * **What it does**: Manages database migrations, tracking revisions to update the PostgreSQL schema over time.
   * **Why we use it**: Ensures database schemas are synchronized across local development, test suites, and production environments without manual SQL interventions.
4. **[PostgreSQL](https://www.postgresql.org/)**
   * **What it does**: Stores decision trees, nodes, edges, references, and runtime logs.
   * **Why we use it**: It is a production-grade relational database with excellent native support for `JSONB` datatypes, which is essential for storing and querying dynamic condition definitions and context patches.
5. **[Astral uv](https://docs.astral.sh/uv/)**
   * **What it does**: Serves as the package manager, virtual environment manager, and command executor.
   * **Why we use it**: It is extremely fast (written in Rust), simplifies dependency resolution, and pins dependencies reliably via `uv.lock` for reproducible environment setups.
6. **[Pytest](https://docs.pytest.org/)**
   * **What it does**: The test runner that executes our suite of unit tests, database integrations, and migration checks.
   * **Why we use it**: It provides powerful, reusable fixture management and allows separating quick unit tests from slower database/migration tests using custom markers.
7. **[Ruff](https://docs.astral.sh/ruff/) and [Pyright](https://github.com/microsoft/pyright)**
   * **What they do**: Ruff acts as the static linter and formatter, while Pyright performs static type checking.
   * **Why we use them**: They enforce uniform style guidelines, catch syntax errors or unused imports, and guarantee type safety across the domain and api layers.

### Frontend Stack (Visualizer)
1. **[React](https://react.dev/) & [TypeScript](https://www.typescriptlang.org/)**
   * **What they do**: Renders the dynamic interactive UI elements and manages the component state, checked with strict typing.
   * **Why we use them**: React's component model fits tree-rendering UI, and TypeScript provides compiler-level type safety when handling tree-graph JSON shapes received from the backend.
2. **[Vite](https://vite.dev/)**
   * **What it does**: Serves as the local bundler, developer server, and asset compiler for the frontend.
   * **Why we use it**: It provides near-instantaneous hot module reloading (HMR) and fast build packaging compared to traditional build systems like Webpack.
3. **[tldraw SDK](https://tldraw.dev/)**
   * **What it does**: Powering the visualizer canvas, it renders the tree nodes and connecting edges on an interactive, infinite pan/zoom whiteboard.
   * **Why we use it**: Offers an out-of-the-box, premium-feeling canvas library for displaying flowchart-like graph visualizations and custom nodes without building canvas interaction logic from scratch.

---

## 🏗️ Architecture and Component Design

The project is structured as a Python modular monolith inside the [src/cdss](file:///c:/Users/Huy/Desktop/cdss/src/cdss) package:

```text
src/cdss/
├── domain/decision_tree/      # Pure clinical traversal engine (No DB or API deps)
│   ├── contracts.py           # Core types, results, and trace models
│   ├── graph.py               # Immutable decision-tree definitions and repo interface
│   ├── walker.py              # Stateless decision-tree traversal engine (walk_tree)
│   ├── conditions.py          # Parsing and evaluation logic for JSON condition definitions
│   ├── patches.py             # Context-patch application (merges and COPY_PATH ops)
│   ├── paths.py               # Dot-notated input and context path resolver
│   ├── validator.py           # Static tree validation (cycle detection, link checks)
│   └── errors.py              # Typed domain errors
├── infrastructure/db/         # SQLAlchemy models and repository implementation
│   ├── models.py              # Database table definitions
│   ├── decision_tree_repository.py  # Bulk graph loading via 4 SQL queries
│   └── caching_repository.py  # Thread-safe in-memory caching wrapper
└── api/                       # Presentation layer
    ├── routes/                # FastAPI routing endpoints (evaluation, fhir, tree_graph)
    └── schemas/               # Request, response, and FHIR schema validations
```

### 1. Domain Layer (`cdss.domain.decision_tree`)
* **[contracts.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/contracts.py)**: Defines runtime container structures, including [RunState](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/contracts.py#L17), [TraversalResult](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/contracts.py#L19), [ExecutedAction](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/contracts.py#L11), [ExecutedReference](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/contracts.py#L12), [NodeType](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/contracts.py#L16), and [TreeMetadata](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/contracts.py#L21).
* **[graph.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/graph.py)**: Contains the immutable domain objects [TreeGraph](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/graph.py#L45), [NodeDefinition](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/graph.py#L42), and [EdgeDefinition](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/graph.py#L41), and the [TreeGraphRepository](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/graph.py#L46) interface.
* **[walker.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/walker.py)**: Contains [walk_tree](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/walker.py#L55), the stateless core engine that executes traversal logic.
* **[conditions.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/conditions.py)**: Evaluates complex boolean structures (`all`, `any`, `not`), comparisons (`eq`, `in`, `lt`, `lte`, `gt`, `gte`), arithmetic subtractions, and path existence.
* **[patches.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/patches.py)**: Implements [apply_context_patch](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/patches.py#L48), executing static recursive merging and ordered `COPY_PATH` operations.
* **[paths.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/paths.py)**: Contains [resolve_runtime_path](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/paths.py#L49) which traverses nested dictionary objects.
* **[validator.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/validator.py)**: Runs static validation checking trees for cycles, start nodes, and broken edge configurations prior to traversal.
* **[errors.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/errors.py)**: Defines strongly-typed domain errors (e.g., [MissingRuntimePath](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/errors.py#L33), [UnsupportedOperator](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/errors.py#L38)).

### 2. Infrastructure Layer (`cdss.infrastructure.db`)
* **[models.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/infrastructure/db/models.py)**: Holds SQLAlchemy representations for `decision_trees`, `decision_nodes`, `decision_edges`, `node_source_references`, and `development_runtime_logs`.
* **[decision_tree_repository.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/infrastructure/db/decision_tree_repository.py)**: Implements [SqlAlchemyTreeGraphRepository](file:///c:/Users/Huy/Desktop/cdss/src/cdss/infrastructure/db/decision_tree_repository.py#L20), utilizing a 4-query loading scheme to load a full tree graph (trees, nodes, edges, references) in batch.
* **[caching_repository.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/infrastructure/db/caching_repository.py)**: Implements [CachingTreeGraphRepository](file:///c:/Users/Huy/Desktop/cdss/src/cdss/infrastructure/db/caching_repository.py#L9), which wraps another repository in a thread-safe in-memory cache.

### 3. API Layer (`cdss.api`)
* **[routes/evaluation.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/api/routes/evaluation.py)**: Implements the stateless clinical evaluation `POST /evaluate` endpoint.
* **[routes/fhir.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/api/routes/fhir.py)**: Exports decision trees as read-only HL7 FHIR R4 resources (`PlanDefinition` and `Library`).
* **[routes/tree_graph.py](file:///c:/Users/Huy/Desktop/cdss/src/cdss/api/routes/tree_graph.py)**: Exposes representation graphs consumed by the Vite visualizer.

---

## 🌳 Traversal Engine Concepts & Node Types

Clinical workflows are evaluated without python-coded branching. Instead, [walk_tree](file:///c:/Users/Huy/Desktop/cdss/src/cdss/domain/decision_tree/walker.py#L55) traverses a decision tree graph. The engine evaluates target branch conditions based on priority (`traversal_order` on edges) and transitions between nodes.

### Node Types
* **`START`**: Exactly one entry point per tree. No side effects; branches out immediately.
* **`CONDITION`**: Evaluates `condition_definition` before allowing entry. Must have at least one outgoing edge.
* **`INFERENCE`**: Applies a `context_patch` on entry (adds derived fields to context) and branches out.
* **`ACTION`**: Collects a structured `action_payload` (e.g. drug regimen) and applies a `context_patch` if present. If outgoing edges exist, continues traversing; otherwise, terminates successfully.
* **`END`**: Applies its `context_patch`, collects its `action_payload`, and terminates successfully.
* **`LINK`**: Transitions control flow to another decision tree by resolving `link_target_tree_key` and optionally `link_target_node_key`. This is a cross-tree tail transfer: execution does not return to the calling tree on completion.
* **`GLOBAL`**: Stores tree-level config metadata (e.g. override limits, age thresholds). Kept in tree metadata but never traversed.

---

## 📜 Decision-Tree JSON Dialect

### 1. Condition Expressions
Branch conditions resolved via target `condition_definition` values support:
* **Operators**: `eq` (strict equality), `exists` (path presence check), `in` (strict array membership check), `lt`, `lte`, `gt`, `gte` (strict numeric comparisons).
* **Nesting**: Logical operators `all` (AND), `any` (OR), and `not` (negation) can nest recursively:
  ```json
  {
    "all": [
      { "path": "input.current_clinic_sbp", "op": "gte", "value": 140 },
      {
        "not": {
          "path": "input.is_medication_follow_up", "op": "eq", "value": true
        }
      }
    ]
  }
  ```
* **Arithmetic Subtraction**: Evaluates a mathematical difference before comparison:
  ```json
  {
    "left": {
      "expression": "subtract",
      "left_path": "input.previous_clinic_sbp",
      "right_path": "input.current_clinic_sbp"
    },
    "op": "gte",
    "value": 10
  }
  ```

### 2. Context Patches
Patches are executed on node entry and can contain static values and operation lists:
* **Static Merge**: JSON objects are recursively merged into `RunState.context`.
* **Ordered Operations**: Evaluated after the merge. Currently supports `COPY_PATH` (deep copies a value from input or context into context):
  ```json
  {
    "treatment": {
      "follow_up_mode": "medication"
    },
    "operations": [
      {
        "op": "COPY_PATH",
        "from_path": "input.active_bp_target",
        "to_path": "context.treatment.bp_target",
        "required": true
      }
    ]
  }
  ```

---

## 🔗 Cross-Tree Context Contract

Because trees execute dynamically, they pass data through a shared, mutable `RunState.context` object. The five seeded trees (`hypertension-diagnosis`, `risk-classification`, `treatment-threshold-and-bp-target`, `essential-treatment-strategy`, `optimal-treatment-strategy`) interact using the following load-bearing paths:

1. **`context.diagnosis.hypertension_class`**: Set by `hypertension-diagnosis`. Read by `risk-classification` to decide risk tier branching.
2. **`context.risk.level`**: Set by `risk-classification`. Read by `treatment-threshold-and-bp-target`, `essential-treatment-strategy`, and `optimal-treatment-strategy` to customize BP targets and regimens.
3. **`context.treatment.bp_target`**: Restored or configured by `treatment-threshold-and-bp-target`. Read by `essential-treatment-strategy` and `optimal-treatment-strategy` to compare current BP against clinical targets.

For complete path schemas, see the design contract in [docs/cdss/context-contract.md](file:///c:/Users/Huy/Desktop/cdss/docs/cdss/context-contract.md).

---

## ⚡ API Specification

Interactive swagger endpoints are available at `http://localhost:8000/docs`.

### 1. Clinical Evaluation Endpoint: `POST /evaluate`
Evaluates decision tree logic statelessly against a clinical input payload.

* **Sample Request**:
  ```json
  {
    "start_tree_key": "treatment-threshold-and-bp-target",
    "input": {
      "is_medication_follow_up": true,
      "is_lifestyle_follow_up": false,
      "active_bp_target": {
        "dbp": {"upper_exclusive_mmhg": 80},
        "sbp": {
          "lower_reference_mmhg": 120,
          "or_lower": true,
          "upper_exclusive_mmhg": 130
        },
        "source": "TREE_3_GENERIC"
      },
      "facility_capability": "FULL_RESOURCES",
      "current_clinic_sbp": 129,
      "current_clinic_dbp": 79
    }
  }
  ```

* **Sample Response**:
  ```json
  {
    "status": "success",
    "input_snapshot": {
      "is_medication_follow_up": true,
      "is_lifestyle_follow_up": false,
      "active_bp_target": { ... },
      "facility_capability": "FULL_RESOURCES",
      "current_clinic_sbp": 129,
      "current_clinic_dbp": 79
    },
    "context": {
      "treatment": {
        "bp_target": {
          "dbp": { "upper_exclusive_mmhg": 80 },
          "sbp": {
            "lower_reference_mmhg": 120,
            "or_lower": true,
            "upper_exclusive_mmhg": 130
          },
          "source": "TREE_3_GENERIC"
        }
      }
    },
    "actions": [
      {
        "tree_key": "optimal-treatment-strategy",
        "node_key": "T5_END_INITIAL_REGIMEN_TARGET_REACHED",
        "node_type": "END",
        "text_en": "Target reached: Maintain current medication regimen",
        "text_vi": "Đạt huyết áp mục tiêu: Tiếp tục duy trì phác đồ điều trị hiện tại",
        "payload": {
          "action_type": "MAINTAIN_CURRENT_REGIMEN",
          "follow_up_mode": "STANDARD_MONITORING",
          "follow_up_required": true
        }
      }
    ],
    "traversal_log": [ ... ],
    "references": [ ... ],
    "tree_metadata": [ ... ],
    "started_at": "2026-07-03T09:00:00Z",
    "completed_at": "2026-07-03T09:00:00.021Z"
  }
  ```

### 2. Visualization Endpoints
* **`GET /trees`**: Lists summary metadata for all seeded decision trees.
* **`GET /trees/{tree_key}/graph`**: Returns a tree graph represented in a custom JSON format designed for rendering inside the tldraw frontend canvas.

### 3. HL7 FHIR R4 Knowledge Export Endpoints
* **`GET /fhir/PlanDefinition`**: Exports all decision trees inside a single FHIR Bundle container.
* **`GET /fhir/PlanDefinition/{tree_key}`**: Exports a single tree represented as an HL7 FHIR `PlanDefinition`.
* **`GET /fhir/Library/{tree_key}`**: Exports global configuration metadata for a tree represented as an HL7 FHIR `Library`.
* *Note: The FHIR export maps condition definitions dynamically from the internal JSON expression dialect to FHIRPath expression structures.*

---

## 🛠️ Local Installation and Setup

### Prerequisites
- **Python 3.12+**
- **uv** ( Astral's Python installer and package manager )
- **Docker** with Compose support
- **Node.js 20+** ( required only for the optional frontend visualizer )

### 1. Spin up and Configure Backend API
```bash
# Sync dependencies and create a virtualenv
uv sync

# Create your local environment configuration file
cp .env.example .env

# Spin up local PostgreSQL container
docker compose up -d postgres

# Run database schema migrations
uv run alembic upgrade head

# Run FastAPI with reload enabled
uv run uvicorn cdss.main:app --reload
```
The API is now running at `http://localhost:8000`.

### 2. Spin up Frontend Visualizer
The visualizer connects to the backend and renders graphs on a canvas:
```bash
cd frontend
npm install
npm run dev
```
The visualizer runs at `http://localhost:5173`.

---

## 🧪 Testing Guide

We write tests using `pytest`. Database tests use `.env.test` configuration explicitly and run on dedicated local PostgreSQL containers to protect development tables.

### Setup Test Databases
```bash
# Start Docker database
docker compose up -d postgres

# Create the separate test databases
docker compose exec postgres createdb -U cdss cdss_test
docker compose exec postgres createdb -U cdss cdss_schema_test

# Create the test environment configuration file
cp .env.test.example .env.test
```

### Running Tests
* **Mock / Unit Tests (No DB connection needed)**:
  ```bash
  uv run pytest -m "not database"
  ```
* **Seeded Traversal & Integration Tests**:
  Requires the five clinical trees to be loaded into the `cdss_test` database.
  ```bash
  uv run pytest -m database tests/db/test_seeded_tree_validation.py tests/db/test_seeded_link_execution.py tests/db/test_mock_patient_scenarios.py tests/api/test_seeded_evaluation.py
  ```
* **Destructive Schema Migration Tests**:
  Verifies Alembic migrations by downgrading to base and upgrading to head on `cdss_schema_test`.
  ```bash
  uv run pytest -m database tests/db/test_schema_migration.py
  ```
* **Code Quality & Type Checking**:
  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  ```

---

## 💾 Database Management, Alembic, and Backups

### Alembic Migrations
```bash
# Apply migrations to database head
uv run alembic upgrade head

# Check current database migration status
uv run alembic current

# Generate a new migration revision
uv run alembic revision --autogenerate -m "describe changes"
```

### Backups (Dump/Restore Scripts)
Database snapshots and utility scripts are located in [backups](file:///c:/Users/Huy/Desktop/cdss/backups) (see [backups/README.md](file:///c:/Users/Huy/Desktop/cdss/backups/README.md)). To refresh your local PostgreSQL instance with production data, run:
```bash
uv run python backups/dump.py && uv run python backups/restore.py
```

---

## 🔗 Intentional External Link Dependencies

The following tree keys are not seeded in the database. Traversing them is expected to yield typed unresolved `LinkTargetNotFound` exceptions containing partial state data:
- `hypertensive-emergency`
- `hypertension-heart-failure`
- `hypertension-older-adults`
- `hypertension-coronary-artery-disease`
- `hypertension-type-2-diabetes`
- `hypertension-chronic-kidney-disease`
- `drug-combination`
- `resistant-hypertension`
