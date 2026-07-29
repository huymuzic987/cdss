# Hypertension Clinical Decision Support System (CDSS) Backend

A stateless, database-driven clinical decision-support API built with FastAPI, SQLAlchemy, and PostgreSQL. The clinical workflow is stored dynamically in the database as decision-tree nodes and edges, allowing a generic, stateless traversal engine to evaluate conditions, apply context patches, and collect actions without hardcoded branching in Python.

A companion Vite + React + tldraw decision-tree visualizer (plus a statistics dashboard) resides in the [frontend](frontend/) directory.

---

## 📚 Documentation

This README is a quickstart and overview. For anything deeper, see `docs/`:

- [docs/architecture.md](docs/architecture.md): the three-layer design, why it's a modular monolith, and the full request flow for `POST /evaluate`.
- [docs/api.md](docs/api.md): every endpoint, with request/response shapes.
- [docs/database.md](docs/database.md): schema, SQLAlchemy models, Alembic migrations.
- [docs/operations.md](docs/operations.md): seeding, backups, restore, port conflicts.
- [docs/deployment.md](docs/deployment.md): Docker images, the production compose stack, the Jenkins pipeline.
- [docs/frontend.md](docs/frontend.md): visualizer and dashboard structure.
- [docs/cdss/json-dialect.md](docs/cdss/json-dialect.md): the decision-tree JSON dialect (condition operators, context patches).
- [docs/cdss/authoring-a-tree.md](docs/cdss/authoring-a-tree.md): how to build a new decision tree.
- [docs/cdss/traversal-engine-contract.md](docs/cdss/traversal-engine-contract.md) and [docs/cdss/context-contract.md](docs/cdss/context-contract.md): the frozen runtime-behavior and inter-tree data contracts.
- [docs/testing.md](docs/testing.md): test database safety rules.

---

## 🛠️ Technology Stack (What and Why)

The project leverages a modern, robust tech stack designed for speed, clinical accuracy, and stateless operation.

### Backend Core Stack
1. **[FastAPI](https://fastapi.tiangolo.com/)**
   * **What it does**: Handles the HTTP request/response cycle, routes evaluations, validates payloads using Pydantic, and generates an OpenAPI schema served through an interactive API reference UI.
   * **Why we use it**: It is extremely fast, fully supports type hints for automatic validation, and offers a stateless architecture ideal for high-throughput decision-support queries.
2. **[SQLAlchemy ORM](https://www.sqlalchemy.org/)**
   * **What it does**: Serves as the Object-Relational Mapper (ORM), translating Python classes into database tables/queries and providing session/transaction management.
   * **Why we use it**: It decouples the clinical traversal engine from raw SQL, facilitates clean database queries (such as the optimized 4-query graph loader), and handles transaction boundaries safely.
3. **[Alembic](https://alembic.sqlalchemy.org/)**
   * **What it does**: Manages database migrations, tracking revisions to update the PostgreSQL schema over time.
   * **Why we use it**: Ensures database schemas are synchronized across local development, test suites, and production environments without manual SQL interventions.
4. **[PostgreSQL](https://www.postgresql.org/)**
   * **What it does**: Stores decision trees, nodes, edges, references, the medicine reference catalog, and imported clinical data for the statistics dashboard.
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

### Frontend Stack (Visualizer + Dashboard)
1. **[React](https://react.dev/) & [TypeScript](https://www.typescriptlang.org/)**
   * **What they do**: Renders the dynamic interactive UI elements and manages the component state, checked with strict typing.
   * **Why we use them**: React's component model fits tree-rendering UI, and TypeScript provides compiler-level type safety when handling tree-graph JSON shapes received from the backend.
2. **[Vite](https://vite.dev/)**
   * **What it does**: Serves as the local bundler, developer server, and asset compiler for the frontend.
   * **Why we use it**: It provides near-instantaneous hot module reloading (HMR) and fast build packaging compared to traditional build systems like Webpack.
3. **[tldraw SDK](https://tldraw.dev/)**
   * **What it does**: Powering the visualizer canvas, it renders the tree nodes and connecting edges on an interactive, infinite pan/zoom whiteboard.
   * **Why we use it**: Offers an out-of-the-box, premium-feeling canvas library for displaying flowchart-like graph visualizations and custom nodes without building canvas interaction logic from scratch.
4. **[Recharts](https://recharts.org/)**
   * **What it does**: Renders the statistics dashboard's charts (bar, line, donut).

---

## 🏗️ Architecture (summary)

The project is a Python modular monolith inside [src/cdss](src/cdss). Full details, including the exact request flow for `POST /evaluate`, are in [docs/architecture.md](docs/architecture.md).

```text
src/cdss/
├── domain/decision_tree/      # Pure clinical traversal engine (no DB or API deps)
├── domain/follow_up.py        # Hypertension-specific follow-up inference (used by the /evaluate route)
├── infrastructure/db/         # SQLAlchemy models and repository implementations
└── api/                       # FastAPI routes and Pydantic schemas
    ├── routes/                # evaluation, tree_graph, tree_layout, fhir, dashboard, health
    └── schemas/                # Request/response and FHIR schema validation
```

**The core idea**: clinical logic lives in the database as decision-tree data (nodes, edges, JSON condition/patch/action documents), not in Python. There is no `if sbp >= 140` anywhere in `src/cdss`. See [docs/architecture.md](docs/architecture.md) for why this is a modular monolith rather than separate services.

---

## 🌳 Traversal Engine Concepts & Node Types

Clinical workflows are evaluated without Python-coded branching. `walk_tree` (`src/cdss/domain/decision_tree/walker.py`) traverses a decision-tree graph, evaluating target branch conditions by priority (`traversal_order` on edges) and transitioning between nodes.

> For the full frozen runtime-behavior contract, see [docs/cdss/traversal-engine-contract.md](docs/cdss/traversal-engine-contract.md).

### Node Types
* **`START`**: Exactly one entry point per tree. No side effects; branches out immediately.
* **`CONDITION`**: Evaluates `condition_definition` before allowing entry. Must have at least one outgoing edge.
* **`INFERENCE`**: Applies a `context_patch` on entry (adds derived fields to context) and branches out.
* **`ACTION`**: Collects a structured `action_payload` (e.g. drug regimen) and applies a `context_patch` if present. If outgoing edges exist, continues traversing; otherwise, terminates successfully.
* **`END`**: Applies its `context_patch`, collects its `action_payload`, and terminates successfully.
* **`LINK`**: Transitions control flow to another decision tree by resolving `link_target_tree_key` and optionally `link_target_node_key`. This is a cross-tree tail transfer: execution does not return to the calling tree on completion.
* **`GLOBAL`**: Stores tree-level config metadata (e.g. override limits, age thresholds). Kept in tree metadata but never traversed.

---

## 📜 Decision-Tree JSON Dialect (summary)

Full grammar, with worked examples pulled from the real seeded trees, is in [docs/cdss/json-dialect.md](docs/cdss/json-dialect.md).

* **Condition operators**: `eq`, `exists`, `in`, `lt`, `lte`, `gt`, `gte`, nested via `all`/`any`/`not`, plus a `subtract` arithmetic expression for comparing a difference against a threshold.
* **Context patches**: a static recursive JSON merge into `RunState.context`, plus ordered `COPY_PATH` operations (deep-copying a value from `input.*` or `context.*` into `context.*`).

---

## 🔗 Cross-Tree Context Contract (summary)

Because trees execute dynamically, they pass data through a shared, mutable `RunState.context` object. This is a real, versioned contract, not an implementation detail. It currently spans 14 seeded trees (`hypertension-diagnosis`, `risk-classification`, `treatment-threshold-and-bp-target`, `essential-treatment-strategy`, `optimal-treatment-strategy`, `drug-combination`, `resistant-hypertension`, `hypertension-type-2-diabetes`, `hypertension-chronic-kidney-disease`, `hypertension-in-pregnancy`, `hypertensive-emergency`, `hypertension-heart-failure`, `hypertension-coronary-artery-disease`, and `hypertension-older-adults`, the last of which is intentionally left unseeded to exercise the unresolved-link failure path). The most load-bearing paths:

1. **`context.diagnosis.hypertension_class`**: Set by `hypertension-diagnosis`. Read by `risk-classification` to decide risk-tier branching.
2. **`context.risk.level`**: Set by `risk-classification`. Read by the treatment-strategy trees to customize BP targets and regimens.
3. **`context.treatment.bp_target`**: Restored or configured by `treatment-threshold-and-bp-target`. Read by the treatment-strategy trees to compare current BP against clinical targets.

For the complete path schema, including keys added by trees added after the original contract, see [docs/cdss/context-contract.md](docs/cdss/context-contract.md).

---

## ⚡ API Specification (summary)

Interactive API docs are at `http://localhost:8000/docs` (served via [Scalar](https://scalar.com/), not the default Swagger UI; the raw OpenAPI JSON is at `/openapi.json`). Full endpoint-by-endpoint reference, including exact request/response shapes and known quirks, is in [docs/api.md](docs/api.md).

### 1. Clinical Evaluation Endpoint: `POST /evaluate`
Evaluates decision tree logic statelessly against a clinical input payload. **`input` must be an HL7 FHIR R4 `Bundle`** (`resourceType: "Bundle"`), not a flat object of clinical fields, it is converted to the engine's flat input format server-side. See [docs/api.md](docs/api.md#12-the-input-bundle-contract) for the full resource-mapping rules and a complete worked example.

* **Sample Request** (abbreviated; a real Bundle carries every clinical input as separate `Patient`/`Observation`/`Condition`/`Parameters` entries):
  ```json
  {
    "start_tree_key": "treatment-threshold-and-bp-target",
    "input": {
      "resourceType": "Bundle",
      "type": "collection",
      "entry": [
        {
          "resource": {
            "resourceType": "Parameters",
            "parameter": [
              { "name": "is_medication_follow_up", "valueBoolean": true },
              { "name": "facility_capability", "valueString": "FULL_RESOURCES" }
            ]
          }
        },
        {
          "resource": {
            "resourceType": "Observation",
            "code": { "coding": [{ "system": "http://loinc.org", "code": "85354-9" }] },
            "extension": [{ "url": "http://cdss.local/fhir/StructureDefinition/reading-role", "valueCode": "current_clinic" }],
            "component": [
              { "code": { "coding": [{ "system": "http://loinc.org", "code": "8480-6" }] }, "valueQuantity": { "value": 129 } },
              { "code": { "coding": [{ "system": "http://loinc.org", "code": "8462-4" }] }, "valueQuantity": { "value": 79 } }
            ]
          }
        }
      ]
    }
  }
  ```

* **Sample Response**:
  ```json
  {
    "status": "success",
    "input_snapshot": { "is_medication_follow_up": true, "facility_capability": "FULL_RESOURCES", "current_clinic_sbp": 129, "current_clinic_dbp": 79 },
    "context": { "treatment": { "bp_target": { "...": "..." } } },
    "actions": [
      {
        "tree_key": "optimal-treatment-strategy",
        "node_key": "T5_END_INITIAL_REGIMEN_TARGET_REACHED",
        "node_type": "END",
        "text_en": "Target reached: Maintain current medication regimen",
        "text_vi": "Đạt huyết áp mục tiêu: Tiếp tục duy trì phác đồ điều trị hiện tại",
        "payload": { "action_type": "MAINTAIN_CURRENT_REGIMEN", "follow_up_mode": "STANDARD_MONITORING", "follow_up_required": true }
      }
    ],
    "traversal_log": [ ],
    "references": [ ],
    "tree_metadata": [ ],
    "started_at": "2026-07-03T09:00:00Z",
    "completed_at": "2026-07-03T09:00:00.021Z"
  }
  ```

### 2. Visualization Endpoints
* **`GET /trees`**: Lists summary metadata for all seeded decision trees.
* **`GET /trees/{tree_key}/graph`**: Returns a tree graph in a custom JSON format designed for rendering inside the tldraw frontend canvas.
* **`GET|PUT|DELETE /trees/{tree_key}/layout`**: Persists the visualizer's saved canvas layout (node positions, connector style).

### 3. HL7 FHIR R4 Knowledge Export Endpoints
* **`GET /fhir/PlanDefinition`**: Exports all decision trees inside a single FHIR Bundle container.
* **`GET /fhir/PlanDefinition/{tree_key}`**: Exports a single tree represented as an HL7 FHIR `PlanDefinition`.
* **`GET /fhir/Library/{tree_key}`**: Exports global configuration metadata for a tree represented as an HL7 FHIR `Library`.
* *Note: The FHIR export maps condition definitions dynamically from the internal JSON expression dialect to FHIRPath expression structures.*

### 4. Clinical Data Import/Export and Statistics Dashboard
* **`POST /fhir/import`**, **`GET /fhir/Patient`**, **`GET /fhir/Patient/{fhir_id}`**: Import/export clinical data (unrelated to `/evaluate`) that backs the dashboard below.
* **`POST /dashboard/seed`**, **`GET /dashboard/summary`**, **`GET /dashboard/patients`**, **`GET /dashboard/patients/{fhir_id}`**: A statistics dashboard over imported clinical data. See [docs/api.md](docs/api.md#5-statistics-dashboard-dashboard) and [docs/operations.md](docs/operations.md) for how to seed it.

---

## 🛠️ Local Installation and Setup

### Prerequisites
- **Python 3.12+**
- **uv** ( Astral's Python installer and package manager )
- **Docker Desktop** (or another Docker Engine) with Compose support, **running**
- **Node.js 20+** ( required only for the optional frontend visualizer )
- **Git** access to this repository (see [Troubleshooting](#-troubleshooting) if it's private and you haven't authenticated yet)

### 1. Clone and configure

```bash
git clone https://github.com/huymuzic987/cdss.git
cd cdss
cp .env.example .env
```

### 2. Spin up and configure the backend API

**macOS / Linux / WSL / Git Bash:**
```bash
# Set link mode to copy (highly recommended if running on WSL/virtual environments on mounted drives)
export UV_LINK_MODE=copy

# Sync dependencies and create a virtualenv
uv sync

# Spin up local PostgreSQL container
docker compose up -d postgres

# Run database schema migrations
uv run alembic upgrade head

# Load the seeded decision trees and medicine catalog (an empty schema alone
# has no clinical data - see docs/operations.md)
docker compose exec -T postgres psql -U cdss -d cdss -f - < backups/seed.sql
# (if you have a local psql client instead: psql -h localhost -p 54321 -U cdss -d cdss -f backups/seed.sql)

# Run FastAPI with reload enabled
./dev.sh
```

**Windows (PowerShell):**
```powershell
# Sync dependencies and create a virtualenv
uv sync

# Spin up local PostgreSQL container
docker compose up -d postgres

# Run database schema migrations
uv run alembic upgrade head

# Load the seeded decision trees and medicine catalog
docker compose exec -T postgres psql -U cdss -d cdss -f - < backups/seed.sql

# Run FastAPI with reload enabled
.\dev.ps1
```

`dev.sh`/`dev.ps1` are both one-line wrappers: they `cd` to the repository root and run `uv run uvicorn cdss.main:app --reload`. Either way, the API is now running at `http://localhost:8000`.

> [!TIP]
> **Restoring a full snapshot instead**: `backups/seed.sql` is a pure-data seed that assumes the schema already exists from Alembic. If you'd rather restore a complete, self-contained snapshot (schema + data, no separate `alembic upgrade` step needed), run `uv run python backups/restore.py` instead of the migrate+seed steps above. It targets your local Docker database only, it refuses to run against any non-local host, and picks the latest committed `backups/cdss_prod_*.sql` snapshot by default. See [docs/operations.md](docs/operations.md) for both workflows in full, including why you should **not** run `backups/dump.py` as a setup step (it reads from whatever `DATABASE_URL` already points at; it isn't a way to fetch data you don't already have).

> [!NOTE]
> **WSL Development Tip**: If you are running the backend in WSL and editing files on a mounted Windows drive (`/mnt/c/...`), WSL `inotify` file watchers may not automatically reload Uvicorn on changes. In such cases, restart Uvicorn manually to apply edits.

### 3. Spin up Frontend Visualizer
The visualizer connects to the backend and renders graphs on an interactive whiteboard canvas, plus a statistics dashboard:
```bash
cd frontend
pnpm install
pnpm dev
```
The visualizer runs at `http://localhost:5173`.

> [!TIP]
> * **Automatic CORS Port Matching**: If port `5173` is already in use, Vite will automatically select a different port (such as `5174`). The backend is configured to accept CORS requests dynamically from any local development port.
> * **Untangling Layouts (Drag & Drop)**: If lines or cards overlap in complex clinical pathways, you can click and drag any node to rearrange the layout. Connected edges (arrows) will automatically stretch and follow the nodes.

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
  Requires the seeded decision trees loaded into the `cdss_test` database (apply migrations, then `backups/seed.sql`, against `cdss_test` - see [docs/operations.md](docs/operations.md)).
  ```bash
  uv run pytest -m database tests/db/test_seeded_tree_validation.py tests/db/test_seeded_link_execution.py tests/db/test_mock_patient_scenarios.py tests/api/test_seeded_evaluation.py
  ```
  The mock-patient scenarios and their expected outcomes are documented in [docs/cdss/mock-patient-test-matrix.md](docs/cdss/mock-patient-test-matrix.md).
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

See [docs/database.md](docs/database.md) for the full migration history and what each revision actually changed.

### Backups (Dump/Restore Scripts)

Database snapshots and utility scripts are located in [backups](backups/) (see [backups/README.md](backups/README.md)). **A fresh local database has no clinical data until you load it** - see step 2 of the setup above, or [docs/operations.md](docs/operations.md) for both seeding workflows in full.

`backups/dump.py` and `backups/restore.py` are not a matched "run both to get set up" pair: `dump.py` reads (read-only) from whatever database `DATABASE_URL` already points at, it is how you *produce* a new snapshot from a database you already trust, not how you populate an empty one. To refresh your local PostgreSQL instance from a committed snapshot, run `restore.py` on its own:

```bash
uv run python backups/restore.py
```

---

## 🩺 Troubleshooting

**Cloning fails with a permission/authentication error (private repository).**
This repository is private on GitHub. Over HTTPS, `git clone` will prompt for credentials; a GitHub account password will not work, use a [personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) as the password (or set up the [GitHub CLI](https://cli.github.com/) with `gh auth login` and let it handle credentials). Over SSH, make sure your public key is added to your GitHub account and, if you use multiple GitHub identities/keys, that your `~/.ssh/config` has a `Host` entry aliasing this repo's host to the right key, matching whatever remote URL you were given.

**`docker compose up -d postgres` fails, or the backend can't connect to Postgres.**
Docker Desktop (or your Docker engine) needs to actually be running first, not just installed. Check with `docker info`; if that errors or hangs, start Docker Desktop (or `sudo systemctl start docker` on Linux) and retry. If Docker is running but the command still fails, see the port-conflict entry below.

**A native PostgreSQL install is already using port 5432, or something else is on port 54321.**
This project's local Postgres container publishes on host port `54321`, not the default `5432`, specifically to avoid this class of conflict (see [compose.yaml](compose.yaml)). If `docker compose up -d postgres` still fails to bind, or `DATABASE_URL` in your `.env` was ever changed to point at `5432`, see [docs/operations.md](docs/operations.md#4-port-conflicts) for how to find out what's actually listening and how to resolve it without touching the container's internal port.

**`.\dev.ps1` is blocked by PowerShell ("running scripts is disabled on this system").**
This is PowerShell's default execution policy, not a bug in this repository. Run `Set-ExecutionPolicy -Scope Process RemoteSigned` in that session (applies only to the current window), or `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once to fix it for your user account, then re-run `.\dev.ps1`.

**The API runs, but every tree lookup 404s / `/evaluate` says a tree wasn't found.**
Running `uv run alembic upgrade head` alone creates empty tables, it does not load any decision trees. See step 2 of [Local Installation and Setup](#2-spin-up-and-configure-the-backend-api) above (`psql -f backups/seed.sql`, or `backups/restore.py` for a full snapshot instead) and [docs/operations.md](docs/operations.md) for the full explanation of why `dump.py` is not the fix here.

---

## 🔗 Intentional External Link Dependencies

The following tree key is not seeded in the database. Traversing it is expected to yield a typed unresolved `LinkTargetNotFound` exception containing partial state data:
- `hypertension-older-adults`
