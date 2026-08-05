# Complete API Reference

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
[Architecture](../architecture.md#request-flow-post-evaluate) for the
full step-by-step request flow (FHIR-Bundle flattening, follow-up inference,
traversal, action collapsing).

**Request body:** the body *is* the FHIR Bundle directly - there is no
wrapper object and no `start_tree_key` request field:

```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [ /* Patient / Condition / Encounter / Observation / MedicationRequest resources - see 1.2 */ ]
}
```

The route's FastAPI signature (`def evaluate(bundle: JsonObject, ...)`) takes
this as its sole non-`Depends` parameter, so Pydantic types it as an
arbitrary JSON object - the Bundle shape is enforced at runtime by
`parse_clinical_bundle()`, not by the schema, so Scalar/OpenAPI will show the
request body as an untyped object with no further structure. See §1.2.

Which tree the traversal starts from is **not** caller-selectable: it's
always `hypertension-diagnosis`, unless the route's own previous-visit
replay (step 3 below) infers a follow-up, in which case it's overridden to
`treatment-threshold-and-bp-target`. Use `POST /evaluate/follow-up` (§1.3) if
you already know the follow-up stage and want to skip that inference.

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
- **`input_snapshot`** is the raw Bundle you sent, echoed back as-is (`parsed.raw_bundle`) -
  it is *not* the flattened `input.*` runtime object the engine actually
  traverses with (that stays server-internal).
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

### 1.2 The Bundle contract

The request body is not a raw dict of clinical fields and not the engine's
native flat format - it must be a FHIR R4 `Bundle`, converted by
**`cdss.api.schemas.clinical_evaluation.parse_clinical_bundle()`** into the
flat `input.*` namespace the traversal engine actually reads. This is the
*same* Patient/Condition/Encounter/Observation/MedicationRequest profile the
clinical-import API and the reference bundles under `data/fhir/test_case`
use - not a bespoke evaluation-only dialect. `Bundle.resourceType` must be
`"Bundle"`, every `entry[i].resource` must be present with a
`resourceType`, and resource ids (when given) must be unique within the
Bundle. Each resource is then routed by `resourceType`:

| Resource | Maps to | Rule |
| --- | --- | --- |
| `Patient` (exactly one, required) | `input.age`, plus extension-driven keys below | `Patient.id` is required and is the subject every other resource's `subject.reference` must match (`Patient/{id}`). `Patient.birthDate` → `input.age` (years as of today). |
| `Patient`/`Encounter` extensions | `input.facility_capability`, `input.risk_factor_count`, or any `input.<key>` | Dedicated: `.../StructureDefinition/facility-capability` (`valueCode`, `"FULL_RESOURCES"` or `"LIMITED_RESOURCES"`; defaults to `FULL_RESOURCES`) and `.../StructureDefinition/risk-factor-count` (`valueInteger`; defaults to `0`). Generic catch-all: any extension whose URL starts with `.../StructureDefinition/input/` becomes `input.<the-rest-of-the-url>`, read from whichever `value[x]` is present (`valueBoolean`/`valueInteger`/`valueDecimal`/`valueString`/`valueCode`/`valueDate`). This is how `/evaluate/follow-up` (§1.3) passes `medication_follow_up_stage`, `active_bp_target_sbp_upper`, `active_bp_target_dbp_upper`, etc. |
| `Encounter` (zero or more) | selects **longitudinal** vs **snapshot** mode | If any `Encounter` is present, every BP `Observation` must reference one (`Observation.encounter`) and the Bundle is in *longitudinal* mode: encounters are sorted by `period.start` (ambiguous same-instant latest → `InvalidFhirInput`), the most recent becomes `current_clinic_sbp`/`dbp` (and its own extensions are applied for `facility_capability`/`risk_factor_count`/generic keys), and the second-most-recent (if any) becomes `previous_sbp`/`dbp`. If no `Encounter` is present, the Bundle is in *snapshot* mode (see next row). |
| `Observation` (blood pressure) | `current_clinic_sbp`/`dbp`, `previous_sbp`/`dbp`, or `home_sbp`/`dbp` | LOINC `8459-0` = SBP, `8462-4` = DBP (matched via `Observation.code.coding` directly - no panel/component wrapper required). In *snapshot* mode (no Encounters), role comes from a `.../StructureDefinition/reading-role` extension with value `current_clinic`, `previous`, or `home`; if no BP Observation carries that extension, the unlabeled pair defaults to `current_clinic`. `current_clinic` is required in every mode; `home` BP requires both `home_sbp` and `home_dbp` together. Missing one side of a pair, conflicting duplicate values, or (in longitudinal mode) a BP Observation with no `encounter` reference all raise `InvalidFhirInput` (422). |
| `Observation` (labs) | `input.acr_mg_mmol`, `input.proteinuria_24h_mg`, plus a `clinical_details` entry | LOINC `9318-7` (ACR) and `2889-4` (24h proteinuria) map to a named flat key *and* a `clinical_details` line item. LOINC `98979-8` (eGFR) and `6298-4` (potassium) are recorded as `clinical_details` line items only - the traversal engine currently has no flat key for them. |
| `Condition` | boolean `input.has_*`/`input.is_*` flag | Two independent mechanisms, both can apply to the same Condition: (1) `Condition`s coded on the local CodeSystem `http://cdss.local/fhir/CodeSystem/clinical-flag` - the code value must be one of the closed-world `KNOWN_BOOLEAN_FLAGS` and becomes that flat key directly; (2) real-world ICD-10/SNOMED codes matched by prefix regardless of CodeSystem coding - `E11*`/SNOMED `44054006` → `has_type_2_diabetes` + `has_diabetes`; `N18*`/SNOMED `709044004` → `has_ckd`; `N18.3`-`N18.6`/SNOMED `433144002` → also `has_ckd_stage_3_or_higher`; `I25*`/SNOMED `53741008` → `has_coronary_artery_disease`. Either way, the flag is `true` unless `verificationStatus` contains `refuted`. Every flag not touched by some Condition defaults to `false`. |
| `MedicationRequest` | `clinical_details` entry only | Recorded for the medication-history display (name + dose); does not set any `input.*` key. |
| `Parameters` | **rejected** | Bundles carrying a `Parameters` resource raise `InvalidFhirInput` (422) - this is a hard difference from the older, no-longer-used dialect below. |
| anything else | ignored | Forward-compatible: unrecognized resource types contribute nothing but don't error. |

Malformed shapes the mapper must act on (bad date, missing/mismatched
`subject.reference`, an Encounter-less BP Observation in longitudinal mode,
an unrecognized BP reading-role, a `Parameters` resource, a duplicate
resource id, more or less than one `Patient`) all raise `InvalidFhirInput` →
HTTP 422.

**A different, older dialect still exists on disk but is not what powers
`/evaluate` or `/evaluate/follow-up`:** `cdss.api.schemas.fhir_input`
(`bundle_to_input()`/`input_to_bundle()`) implements an earlier
`Parameters`-resource-as-catch-all convention. It's neither imported by
`evaluation.py` nor `evaluation_follow_up.py` - it's exercised only by its
own tests (`tests/api/test_fhir_input.py`,
`tests/api/test_condition_fhirpath.py`). Don't use it as a reference for what
the live endpoints accept; use this table, or the frontend's port of the
*current* dialect in `frontend/src/panels/mockPatientForm/fhirBundle.ts`.

### 1.3 `POST /evaluate/follow-up`

A narrower sibling of `/evaluate`
(`src/cdss/api/routes/evaluation_follow_up.py`), added to reach medication
follow-up outcomes `/evaluate` cannot: `/evaluate`'s previous-visit replay
(§1) forces `is_medication_follow_up=false` on that replay, so it can only
ever conclude `medication_follow_up_stage == "INITIAL_REGIMEN"` for today's
visit - there is no path by which it can conclude `"ESCALATED_REGIMEN"`, so
`resistant-hypertension` (only reachable from the escalated-and-target-not-
reached branch of `essential-treatment-strategy`/`optimal-treatment-strategy`)
is unreachable through `/evaluate` for any input. This endpoint skips that
replay/inference entirely and requires the caller to already know the stage
and BP target - the caller decides, not a two-BP-reading heuristic.

**Request body:** the request body *is* the FHIR Bundle directly (same
convention as `/evaluate` - there is no `{"input": ...}` wrapper; see §1.2 for
how `Patient`/`Observation`/`Condition` resources map to flat `input.*` keys).
In addition to `current_clinic_sbp`/`current_clinic_dbp` (from a blood-pressure
`Observation`), the route requires three more flat keys, supplied as
`http://cdss.local/fhir/StructureDefinition/input/<key>` extensions on the
`Patient` resource (the same generic mechanism any `input.*` key not
special-cased by the resource mapper uses):

- `medication_follow_up_stage` (`valueString`: `"INITIAL_REGIMEN"` or `"ESCALATED_REGIMEN"`)
- `active_bp_target_sbp_upper` (`valueDecimal`)
- `active_bp_target_dbp_upper` (`valueDecimal`)

The route assembles these two numbers into
`context.treatment.bp_target = {"sbp": {"upper_exclusive_mmhg": ...}, "dbp": {"upper_exclusive_mmhg": ...}}`
and forces `is_medication_follow_up=true`, `is_lifestyle_follow_up=false`
before walking `treatment-threshold-and-bp-target`. Missing any of the five
required keys raises `InvalidFhirInput` (422) - **this requirement is
enforced in route code, not expressed in the OpenAPI schema**, so Scalar will
only show the bundle's own `resourceType`/`entry` shape as required.

**Success response:** same `EvaluationResponse` shape as `/evaluate`, except
`inferred_follow_up_type` and `previous_recommended_action_types` are always
`null`/`[]` (this endpoint never runs follow-up inference).

**Errors:** same 404/422/424/500 set as `/evaluate`.

**By design, currently pending frontend work:** the traversal engine's walker
only continues past an `ACTION` node for a small tree allowlist
(`essential-treatment-strategy`, `optimal-treatment-strategy`, and one
`hypertension-in-pregnancy` node) - `resistant-hypertension` is not on that
allowlist, so a traversal that reaches it halts at the first `ACTION` node
(e.g. `T13_A_CHECK_MRA`) instead of continuing on
`tolerates_mra`/`tolerates_spironolactone`/`bp_target_reached`. This is
intentional: `resistant-hypertension` is meant to stop there so the frontend
can show an interactive modal for a doctor to confirm/provide that
information before traversal resumes, not a gap to close by adding the tree
to the allowlist. That modal, and whatever mechanism resumes the halted
traversal with the doctor's input, is still being built (owned outside this
change) - until it lands, a call that reaches this tree simply stops at the
ACTION node.

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
canvas renders (see [Frontend](../frontend.md)).

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

Backs the frontend's dashboard view (see [Frontend](../frontend.md)).
Entirely reads/writes the clinical-data tables from §4.4 - none of this
touches decision trees or the traversal engine.

### 5.1 `POST /dashboard/seed`

Loads one of three bundled FHIR datasets via the same import path as
`POST /fhir/import`. Query param `source` (required):
`"preset"` | `"synthetic"` | `"real_test_case"`.

- `preset` / `synthetic` load `data/fhir/preset_patients.json` (40 patients,
  including 20 drug-contraindication cases)
  or `data/fhir/synthetic_patients.json` (1,000 patients) - see
  [Operations](../operations.md).
- `real_test_case` imports every `backups/test_case/*.json` file (a
  directory that is **not committed to this repository** and must be
  provisioned locally - see [Operations](../operations.md)); if the
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
[Deployment](../deployment.md).
