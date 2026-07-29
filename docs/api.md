# API Reference

The backend is a FastAPI app (`cdss.main.create_app()`). Interactive,
always-current API docs are served at **`http://localhost:8000/docs`**. That
route does not use FastAPI's default Swagger UI - `cdss.main` disables it
(`docs_url=None`) and instead serves the same OpenAPI schema through
[Scalar](https://scalar.com/)'s API reference UI
(`scalar_fastapi.get_scalar_api_reference`). The raw OpenAPI JSON is still at
`/openapi.json` if you want to feed it into a different tool (Swagger UI,
Postman, a codegen tool, etc). This document exists because the two most
important request bodies (`/evaluate`'s `input`, and the FHIR Bundle shape it
requires) are typed as opaque JSON objects at the Pydantic level, so the
Scalar/OpenAPI view alone won't show you their real structure - see §1.2.

All endpoints are unversioned (no `/v1` prefix). CORS is wide open
(`allow_origins=["*"]`) because no patient identifier crosses this API.

## Routers

| Router | Prefix | File |
| --- | --- | --- |
| health | - | `src/cdss/api/routes/health.py` |
| evaluation | - | `src/cdss/api/routes/evaluation.py` |
| tree-graph | - | `src/cdss/api/routes/tree_graph.py` |
| tree-layout | - | `src/cdss/api/routes/tree_layout.py` |
| fhir | `/fhir` | `src/cdss/api/routes/fhir.py` |
| dashboard | `/dashboard` | `src/cdss/api/routes/dashboard.py` |

## Shared error shape

Every domain error (404/422/424/500 across almost all routes) and every
request-validation failure (422) serializes as `EvaluationErrorResponse`:

```json
{
  "code": "no_matching_transition",
  "message": "No outgoing transition matched from node '...' in tree '...'. Tested 3 candidate transitions, but none evaluated to true.",
  "tree_key": "treatment-threshold-and-bp-target",
  "node_key": "T3_C_SOME_NODE",
  "details": { "outgoing_candidate_count": 3 },
  "partial_run_state": {
    "input_snapshot": { "...": "..." },
    "context": { "...": "..." },
    "actions": [ ],
    "traversal_log": [ ],
    "references": [ ]
  }
}
```

`partial_run_state` is populated only for traversal failures that happen
mid-run (e.g. `MissingRuntimePath`, `NoMatchingTransition`,
`LinkTargetNotFound`) - it lets a caller see exactly how far the tree got,
including every action/trace-entry/reference recorded before the failure.
`message` is a hand-written, human-readable string built per error type in
`src/cdss/api/errors.py`; `code` is the stable machine-readable identifier
(`tree_not_found`, `missing_runtime_path`, `no_matching_transition`,
`link_target_not_found`, `link_target_node_not_found`,
`traversal_cycle_detected`, `traversal_limit_exceeded`, `link_not_enabled`,
`invalid_fhir_input`, `invalid_request`, and others - see
`src/cdss/domain/decision_tree/errors.py` for the full set).

Status-code mapping: `TreeNotFound` → 404; `LinkTargetNotFound` /
`LinkTargetNodeNotFound` → 424 (Failed Dependency - the tree itself is fine,
a tree it tried to link into is missing); `MissingRuntimePath` /
`InvalidRuntimeValueType` / `NoMatchingTransition` / `InvalidFhirInput` → 422;
everything else → 500. A malformed request body (wrong type, missing
required field) is caught by FastAPI's own validator and returned as 422
with `code: "invalid_request"` and `details.errors` listing each violation.

**Known inconsistency:** `GET /fhir/Library/{tree_key}` (when the tree has no
`GLOBAL` nodes) and `GET /fhir/Patient/{fhir_id}` (when the patient doesn't
exist) both raise a plain FastAPI `HTTPException(404, detail=...)` instead of
`EvaluationErrorResponse`, even though their OpenAPI spec declares a 404
`EvaluationErrorResponse` body. Their actual 404 body is `{"detail": "..."}`.
Every other declared 404 in this API (`TreeNotFound` cases) does return the
documented shape.

---

## 1. Evaluation

### 1.1 `POST /evaluate`

The main clinical endpoint. See
[docs/architecture.md](architecture.md#request-flow-post-evaluate) for the
full step-by-step request flow (FHIR-Bundle flattening, follow-up inference,
traversal, action collapsing).

**Request body:**

```json
{
  "start_tree_key": "hypertension-diagnosis",
  "input": {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [ /* Patient / Observation / Condition / Parameters resources - see 1.2 */ ]
  }
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `start_tree_key` | string, required | Non-empty, whitespace-stripped. Any seeded `tree_key` (`GET /trees`). |
| `input` | object, required | **Must be an HL7 FHIR R4 `Bundle`** (`resourceType == "Bundle"`). Pydantic only types this as an arbitrary JSON object - the Bundle shape is enforced at runtime, not by the schema, so Scalar/OpenAPI will show `input: object` with no further structure. See §1.2. |

**Success response (200) - `EvaluationResponse`:**

```json
{
  "status": "success",
  "input_snapshot": { "...": "the flattened runtime input actually used" },
  "context": { "...": "final RunState.context" },
  "actions": [
    {
      "tree_key": "optimal-treatment-strategy",
      "node_key": "T5_END_INITIAL_REGIMEN_TARGET_REACHED",
      "node_type": "END",
      "text_en": "Target reached: Maintain current medication regimen",
      "text_vi": "Đạt huyết áp mục tiêu: Tiếp tục duy trì phác đồ điều trị hiện tại",
      "payload": { "action_type": "MAINTAIN_CURRENT_REGIMEN", "...": "..." }
    }
  ],
  "traversal_log": [ /* TraversalTraceEntry[] - see below */ ],
  "references": [ /* ExecutedReference[] */ ],
  "tree_metadata": [ /* TreeMetadata[] - one per tree touched, incl. GLOBAL config */ ],
  "started_at": "2026-07-03T09:00:00Z",
  "completed_at": "2026-07-03T09:00:00.021Z",
  "inferred_follow_up_type": null,
  "previous_recommended_action_types": []
}
```

Field notes:
- **`actions` is filtered by default.** `select_output_actions()` collapses a
  run's action trail down to just the **last** action (the tree's real
  terminal recommendation) unless the server has `CDSS_DEBUG_OUTPUT=true` set
  - in which case every ACTION/END node's payload is returned, including
  intermediate audit-only steps (e.g. `drug-combination`'s duplicate-class
  check). This is a server-side config toggle, invisible to the caller;
  don't assume `actions` is the full trail.
- **`input_snapshot`** is the *flattened* input actually used for traversal -
  it reflects `bundle_to_input()`'s output and any follow-up-inference
  rewriting, not the raw `input` Bundle you sent.
- **`inferred_follow_up_type`** (`"INITIAL_VISIT" | "LIFESTYLE_FOLLOW_UP" |
  "MEDICATION_FOLLOW_UP" | null`) and **`previous_recommended_action_types`**
  are only populated when the route auto-detected a follow-up from
  `previous_sbp`/`previous_dbp` in the flattened input (see §1.2 and
  `docs/architecture.md`). This detection is driven entirely by which fields
  are present in the Bundle you send - there is no explicit "this is a
  follow-up" request flag.
- `TraversalTraceEntry`: `step` (int, ≥1), `event`
  (`"node_entered" | "candidate_evaluated"`), `tree_key`, `node_key`,
  `node_type`, plus for candidate evaluations: `candidate_node_key`,
  `condition_definition`, `condition_result`, `evaluation_details`, and
  `changed_context_paths` (paths a context patch just wrote).
- `ExecutedReference`: `tree_key`, `node_key`, `reference_order`,
  `source_title`, `section_path`, `locator`, `locator_detail`,
  `printed_page_numbers`, `pdf_page_numbers`, `reference_note`.
- `TreeMetadata`: `tree_key`, `name_en`, `name_vi`, `tree_id`,
  `global_config` (list of each `GLOBAL` node's opaque config object, in
  `display_order`).

**Errors:** 404 (`TreeNotFound`), 422 (`MissingRuntimePath`,
`InvalidRuntimeValueType`, `NoMatchingTransition`, `InvalidFhirInput`), 424
(`LinkTargetNotFound`, `LinkTargetNodeNotFound`), 500 (everything else,
including `TraversalCycleDetected`/`TraversalLimitExceeded`, which should
never happen against a validated seeded tree).

### 1.2 The `input` Bundle contract

`input` is not a raw dict of clinical fields and not the engine's native flat
format - it must be a FHIR R4 `Bundle`, converted by
`cdss.api.schemas.fhir_input.bundle_to_input()` into the flat `input.*`
namespace the traversal engine actually reads (roughly 90 ad-hoc keys
accumulated across the 14 seeded trees). Each `Bundle.entry.resource` is
routed by `resourceType`:

| Resource | Maps to | Rule |
| --- | --- | --- |
| `Patient` | `input.age` | Computed from `Patient.birthDate` (years as of today). |
| `Observation` (blood pressure) | one of three reading-role key pairs | Must carry LOINC panel `85354-9` with SBP (`8480-6`)/DBP (`8462-4`) components, plus a local `reading-role` extension (`http://cdss.local/fhir/StructureDefinition/reading-role`, value `current_clinic`, `previous_visit`, or `clinic_1`) selecting whether it becomes `current_clinic_sbp`/`dbp`, `previous_sbp`/`dbp`, or `clinic_1_sbp`/`dbp`. Missing/unrecognized role → `InvalidFhirInput` (422). |
| `Observation` (labs) | `input.acr_mg_mmol` or `input.proteinuria_24h_mg` | Matched by LOINC code `9318-7` / `2889-4`. |
| `Condition` | boolean `input.has_*`/`input.is_*` flag | Only `Condition`s coded on the local CodeSystem `http://cdss.local/fhir/CodeSystem/clinical-flag`; the code value becomes the flat key. `true` unless `verificationStatus` contains `refuted`. |
| `Parameters` | everything else | One `input.*` key per `Parameters.parameter.name` - the catch-all for workflow/orchestration state (`facility_capability`, `active_bp_target`, `medication_follow_up_stage`, ...) and any key the mapper doesn't special-case. Nested objects/arrays are encoded via `parameter.part` (arrays carry a `parameter-is-array` extension so a single-element array isn't mistaken for a scalar). |
| anything else | ignored | Forward-compatible: unrecognized resource types contribute nothing but don't error. |

Malformed shapes the mapper must act on (bad date, missing subject reference,
unrecognized BP reading-role) raise `InvalidFhirInput` → HTTP 422.

`cdss.api.schemas.fhir_input.input_to_bundle()` is the reverse mapping (flat
`input.*` → `Bundle`). It isn't used by any route, but it exists specifically
so integrators and tests don't have to hand-write FHIR resources - see
`tests/api/test_condition_fhirpath.py` / `test_fhir_input.py` for worked
examples, or the frontend's own port of the same logic in
`frontend/src/panels/mockPatientForm/fhirBundle.ts`.

### 1.3 `POST /evaluate/follow-up`

A narrower sibling of `/evaluate`. It skips the previous-visit replay/
inference step entirely - the caller must already know the active BP target
and always starts from `treatment-threshold-and-bp-target`.

**Request body:** `{ "input": <FHIR Bundle> }` (same `EvaluationRequest.input`
typing as above). After flattening via `bundle_to_input()`, the route
requires these five keys to be present in the flattened result, or it raises
`InvalidFhirInput` (422) - **this requirement is enforced in route code, not
expressed in the OpenAPI schema**, so Scalar will only show `input: object`
as required:

- `facility_capability`
- `medication_follow_up_stage`
- `active_bp_target`
- `current_clinic_sbp`
- `current_clinic_dbp`

**Success response:** same `EvaluationResponse` shape as `/evaluate`, except
`inferred_follow_up_type` and `previous_recommended_action_types` are always
`null`/`[]` (this endpoint never runs follow-up inference).

**Errors:** same 404/422/424/500 set as `/evaluate`.

---

## 2. Tree graph (visualizer data)

### 2.1 `GET /trees`

Lists every seeded tree's identity. No query params.

**Response (200):** `TreeSummary[]`

```json
[{ "tree_key": "hypertension-diagnosis", "name_en": "Hypertension Diagnosis", "name_vi": "Chẩn đoán THA" }]
```

### 2.2 `GET /trees/{tree_key}/graph`

Returns one tree's full structure as loaded and validated by the same
`TreeGraphRepository` the traversal engine uses - this is what the frontend
canvas renders (see [docs/frontend.md](frontend.md)).

**Response (200):** `TreeGraphResponse`

```json
{
  "tree": { "tree_key": "...", "name_en": "...", "name_vi": "..." },
  "start_node_key": "T1_START",
  "nodes": [
    {
      "node_key": "T1_C_SBP_CHECK", "node_type": "CONDITION",
      "text_en": "...", "text_vi": "...",
      "condition_definition": { "...": "..." }, "context_patch": null,
      "action_payload": null,
      "link_target_tree_key": null, "link_target_node_key": null,
      "display_order": 0
    }
  ],
  "edges": [{ "from_node_key": "T1_START", "to_node_key": "T1_C_SBP_CHECK", "traversal_order": 0 }],
  "global_nodes": [{ "node_key": "T1_GLOBAL_CONFIG", "text_en": "...", "text_vi": "...", "global_config": { "...": "..." }, "display_order": 0 }],
  "references": [{ "node_key": "T1_C_SBP_CHECK", "source_title": "...", "section_path": [ ], "reference_order": 0, "locator": null, "locator_detail": null, "reference_note": null }]
}
```

`GLOBAL` nodes are excluded from `nodes` and reported separately in
`global_nodes`, matching the domain rule that `GLOBAL` nodes are metadata,
never traversed.

**Errors:** 404 (`TreeNotFound`).

---

## 3. Tree layout (editor canvas persistence)

Persists the visualizer canvas's per-node `(x, y)` positions and connector
style, shared across users/machines (replacing what used to be
browser-`localStorage`). Kept entirely separate from tree structure: a layout
is mutable and saved on every drag, tree structure is treated as immutable.

### 3.1 `GET /trees/{tree_key}/layout`

**Response (200):** `TreeLayoutResponse`

```json
{
  "positions": { "T1_START": { "x": 0, "y": 0 } },
  "arrow_kind": "elbow",
  "edge_layouts": { "T1_START->T1_C_SBP_CHECK": { "...": "..." } }
}
```

If no layout has ever been saved for this tree, this **does not 404**: it
returns the defaults `positions: {}`, `arrow_kind: "elbow"`,
`edge_layouts: {}`.

### 3.2 `PUT /trees/{tree_key}/layout`

**Request body:** `TreeLayoutRequest`

```json
{
  "positions": { "T1_START": { "x": 0, "y": 0 } },
  "arrow_kind": "elbow",
  "edge_layouts": {}
}
```

`positions` and `arrow_kind` (`"straight" | "elbow"`) are required;
`edge_layouts` defaults to `{}`. Upserts the tree's one layout row.

**Response (200):** `TreeLayoutResponse` (the saved state).

### 3.3 `DELETE /trees/{tree_key}/layout`

Deletes the saved layout (the frontend's "reset layout" action, which then
recomputes an automatic ELK layout client-side). **Response: `204 No
Content`.**

**Errors (all three):** 404 (`TreeNotFound`).

---

## 4. FHIR knowledge export (`/fhir`)

Read-only export of the decision-tree knowledge base as HL7 FHIR R4
resources. Condition definitions are dynamically translated from the
internal JSON dialect to FHIRPath expressions (`condition_to_fhirpath()` in
`schemas/fhir.py`).

### 4.1 `GET /fhir/PlanDefinition`

All trees, each as a `PlanDefinition`, wrapped in a `Bundle`
(`type: "searchset"`). No query params.

### 4.2 `GET /fhir/PlanDefinition/{tree_key}`

One tree as a `PlanDefinition`: `resourceType`, `id`, `status: "active"`,
`type`, `name`, `title`, `library` (references to the matching `Library`
resource), and `action[]` - one FHIR `PlanDefinition.action` per node, with
`condition[].expression.expression` holding the FHIRPath translation of that
node's `condition_definition` and `relatedAction`/`definitionCanonical`
encoding the graph's edges/links. Serialized with
`response_model_exclude_none=True`, so absent optional fields are omitted
entirely rather than sent as `null`.

**Errors:** 404 (`TreeNotFound`).

### 4.3 `GET /fhir/Library/{tree_key}`

The tree's `GLOBAL`-node configuration as a FHIR `Library`
(`resourceType`, `id`, `status`, `type`, `content[]` - one `Attachment` per
`GLOBAL` node, base64-ish `data` payload).

**Errors:** 404 - **but see the "known inconsistency" note above**: when a
tree simply has no `GLOBAL` nodes, this 404 is a bare
`{"detail": "tree '...' has no GLOBAL nodes"}`, not an
`EvaluationErrorResponse`, even though that's what's declared in the OpenAPI
spec. A 404 from the tree itself not existing (via `repository.get_tree()`)
would be the documented shape.

### 4.4 `POST /fhir/import`

Imports a FHIR R4 Bundle of `Patient`/`Condition`/`Encounter`/`Observation`/
`MedicationRequest` resources into the clinical dashboard's tables
(`patients`, `patient_conditions`, `visits`, `visit_observations`,
`visit_medications`), upserting by `Patient.id`/`Encounter.id`. This is
entirely separate data from anything `/evaluate` reads - it exists to back
the statistics dashboard (§6), not the traversal engine.

**Request body:** raw `dict` (not Pydantic-validated as a typed FHIR schema -
parsing is deliberately lenient dict access, since real-world bundles vary in
shape; a single malformed resource is recorded in the response and skipped,
not fatal to the whole import). Query param: `source_label` (string, default
`"manual-import"`).

**Response (200):** `ImportResult`

```json
{ "source_label": "manual-import", "patients_imported": 3, "visits_imported": 5, "error_count": 0, "errors": [] }
```

### 4.5 `GET /fhir/Patient`

Exports an (optionally filtered) cohort of imported patients as a FHIR
`Bundle` (`type: "searchset"`), each patient expanded into its full
`Patient`/`Condition`/`Encounter`/`Observation`/`MedicationRequest` resource
set.

**Query params:** `facility_capability` (string), `comorbidity_icd10`
(string), `limit` (int, default 100, max 500).

### 4.6 `GET /fhir/Patient/{fhir_id}`

One patient's full record as a `Bundle`.

**Errors:** intended 404 when not found, but - same inconsistency as §4.3 -
raised as a plain `HTTPException`, body `{"detail": "patient '...' not found"}`,
not `EvaluationErrorResponse`, despite the OpenAPI spec declaring the latter.

---

## 5. Statistics dashboard (`/dashboard`)

Backs the frontend's dashboard view (see [docs/frontend.md](frontend.md)).
Entirely reads/writes the clinical-data tables from §4.4 - none of this
touches decision trees or the traversal engine.

### 5.1 `POST /dashboard/seed`

Loads one of three bundled FHIR datasets via the same import path as
`POST /fhir/import`. Query param `source` (required):
`"preset"` | `"synthetic"` | `"real_test_case"`.

- `preset` / `synthetic` load `data/fhir/preset_patients.json` (20 patients)
  or `data/fhir/synthetic_patients.json` (1,000 patients) - see
  [docs/operations.md](operations.md).
- `real_test_case` imports every `backups/test_case/*.json` file (a
  directory that is **not committed to this repository** and must be
  provisioned locally - see [docs/operations.md](operations.md)); if the
  directory is missing or empty, this raises a plain
  `HTTPException(404, ...)`.

**Response (200):** `ImportResult` (same shape as §4.4; for `real_test_case`,
aggregated across every file in the directory).

### 5.2 `GET /dashboard/summary`

The dashboard's main payload - every section respects the same filter set.

**Query params:** `department` (string), `min_age`/`max_age` (int, ≥0),
`gender` (string), `comorbidity_icd10` (string), `adherent_to_cdss` (bool).

**Response (200):** `DashboardSummaryResponse`, a composite of seven
sections:

- **`overview`**: total patients/visits, new-patient count (last 30 days),
  age/gender/comorbidity/risk-factor-count distributions.
- **`visits`**: follow-up counts, on-schedule vs. early-revisit rate (and a
  reason breakdown), average days between visits, visit-number histogram,
  and up to 50 overdue patients (past their `scheduled_next_visit_date`).
- **`outcomes`**: BP-target distribution, per-visit-number BP-control rate
  and mean SBP/DBP, SBP-severity buckets, overall mean/median SBP.
- **`cdss_usage`**: facility-capability, hypertension-class, and risk-level
  distributions; top-10 most frequent recommended actions; drug-class
  distribution across actually-prescribed medications.
- **`efficacy`**: adherence-to-CDSS-recommendation rate, and BP-control
  rate when adherent vs. not. **This comparison is deliberately
  cross-visit** (adherence at visit *N* vs. control at visit *N+1*), not
  same-visit - a same-visit comparison would be circular, since a visit is
  only marked non-adherent when its own BP wasn't already controlled. Also
  reports medication-change count/rate and per-visit-number adherence rate.
- **`fhir_import_status`**: recent import batches (source, timestamp,
  counts, errors) and running totals of patients/encounters/observations/
  medication requests.
- **`needs_attention`**: up to 100 patients whose most recent visit has
  uncontrolled BP, is overdue, or was a recent early revisit, sorted by how
  many of those reasons apply.

### 5.3 `GET /dashboard/patients`

Search/browse patients. There is no patient name anywhere in this data model
(FHIR imports carry only id/gender/birth date/department), so `q` matches
against `fhir_id`/`department`, not a name.

**Query params:** `q` (string), `gender` (string), `status`
(`"overdue" | "bp_not_controlled" | "early_revisit"`), `limit` (int, default
25, max 100), `offset` (int, default 0). Independent of `/summary`'s cohort
filter bar.

**Response (200):** `PatientListResponse` - `items[]` (id, gender, birth
date, department, last visit date, visit count, last BP-controlled flag,
last risk level, overdue flag) and `total`.

### 5.4 `GET /dashboard/patients/{fhir_id}`

One patient's full detail: demographics, risk-factor count, coded
conditions, and every visit (readings, targets, control flag, hypertension
class/risk level, recommended action, adherence flag, medications,
observations).

**Errors:** 404 via plain `HTTPException` (no `responses` model declared on
this route - consistent behavior, not a mismatch).

---

## 6. Health

### `GET /health`

No auth, no database dependency. Returns `{"status": "ok", "environment": "development"}`
(`environment` mirrors `APP_ENV`). Used as the container healthcheck by
`Dockerfile.backend` and `docker-compose.prod.yml` - see
[docs/deployment.md](deployment.md).
