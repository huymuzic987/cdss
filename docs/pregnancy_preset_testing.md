# Tree 12 Pregnancy Presets — Complete Test Guide

## What the catalog covers

The Patient Simulator now loads 21 committed FHIR R4 Bundles from
`data/fhir/pregnancy_presets`:

- 13 single-visit Bundles cover initial pregnancy assessment branches.
- 4 targeted two-Encounter Bundles cover high-risk and postpartum follow-up branches.
- 4 longitudinal Bundles cover the initial pregnancy visit plus follow-ups 1, 2, and 3.
- Every preset is tested through both automatic evaluation and manual trace replay.
- The union of the presets executes every non-global node currently present in Tree 12.

The presets are generated deterministically by
`scripts/generate_pregnancy_fhir_presets.py`. Do not hand-edit a generated JSON file without also
updating the generator.

`backups/seed.sql` is not modified by this preset implementation. Legacy pregnancy entry and
precedence compatibility is isolated in
`src/cdss/infrastructure/db/runtime_graph_overrides.py`. The repository applies that overlay when
it builds the immutable in-memory graph, so evaluation, graph display, manual traversal, and FHIR
tree exports all use the same effective relationships without rewriting persisted seed data.

## FHIR R4 profile used by the presets

Each preset follows the same shape as the reference Bundles in `data/fhir/test_case`:

- `resourceType: "Bundle"` and `type: "collection"`;
- a Bundle `id`, `identifier`, `timestamp`, and metadata tags;
- an absolute `fullUrl` for every entry;
- exactly one female Patient with a stable FHIR `id`, `birthDate`, and address;
- confirmed, active Condition resources for clinical flags;
- LOINC-coded Observation resources with UCUM quantities;
- a complete systolic/diastolic pair for clinic and home BP;
- 24-hour protein and ACR laboratory Observations;
- Encounter resources and Encounter-linked BP Observations for longitudinal follow-ups.

The CDSS-specific extensions are valid FHIR R4 extensions. They preserve simulator inputs that do
not have a single suitable core R4 element, including:

```text
http://cdss.local/fhir/StructureDefinition/input/{field}
http://cdss.local/fhir/StructureDefinition/reading-role
http://cdss.local/fhir/StructureDefinition/risk-factor-count
```

The official HL7 FHIR R4 JSON schema in `tests/fhir/schema/fhir.schema.json` validates all 21
Bundles during the backend test suite.

## Pregnancy and targeted follow-up preset matrix

Open **Patient Simulator → Preset Patient → Pregnancy & Postpartum**.

| Preset | Distinguishing input | Expected Tree 12 outcome |
|---|---|---|
| Pregnancy — Normotensive Monitoring | Clinic 120/75, home 120/75 | `T12_END_FOLLOW_UP_MONITOR` |
| Pregnancy Follow-Up — High Preeclampsia Risk (Aspirin) | Prior hypertensive encounter; currently normotensive + high-risk flag | `T12_END_ASPIRIN_PROPHYLAXIS` |
| Pregnancy — Pre-Existing (Chronic) Hypertension | Pre-pregnancy HTN + proteinuria persisting >6 weeks | `T12_END_PRE_EXISTING_HTN` |
| Pregnancy — Gestational Hypertension, Mild/Moderate (Refer) | Clinic 150/95 after week 20 | `T12_END_REFER_OBGYN` |
| Pregnancy — Gestational Hypertension via Home BP (Maintain) | Home 138/87, clinic 140/85 | `T12_END_MAINTAIN_REGIMEN_PREGNANT` |
| Pregnancy — Severe Gestational HTN with Hypertensive Crisis | Clinic 165/110 + crisis flag | `T12_END_REFER_OBGYN` |
| Pregnancy — Severe Gestational HTN with Pulmonary Edema | Clinic 165/110 + pulmonary-edema flag | `T12_END_REFER_OBGYN` |
| Pregnancy — Preeclampsia by 24-Hour Protein (Target Met) | Protein 350 mg/24 h, clinic 140/85 | `T12_END_MAINTAIN_REGIMEN_PREGNANT` |
| Pregnancy — Preeclampsia by ACR (Emergency Delivery) | ACR 35 mg/mmol, clinic 165/110 | `T12_END_EMERGENCY_DELIVERY` |
| Pregnancy — Preeclampsia by Risk Factor (Target Met) | Gestational HTN + diabetes | `T12_END_MAINTAIN_REGIMEN_PREGNANT` |
| Pregnancy — Eclampsia (Immediate Target Met) | Preeclampsia + seizure, clinic 140/85 | `T12_END_MAINTAIN_REGIMEN_PREGNANT` |
| Pregnancy — Eclampsia (Emergency Delivery) | Preeclampsia + seizure, clinic 165/110 | `T12_END_EMERGENCY_DELIVERY` |
| Pregnancy — HELLP Syndrome (Immediate Target Met) | Hemolysis + elevated liver enzymes + low platelets | `T12_END_MAINTAIN_REGIMEN_PREGNANT` |
| Pregnancy — HELLP Syndrome (Emergency Delivery) | HELLP triad + clinic 165/110 | `T12_END_EMERGENCY_DELIVERY` |
| Postpartum Follow-Up — Breastfeeding Guidance | Prior hypertensive encounter; postpartum + breastfeeding | `T12_END_MAINTAIN_REGIMEN_POSTPARTUM` |
| Postpartum Follow-Up — BP Still High | Prior hypertensive encounter; postpartum, clinic 145/95 | `T12_END_MAINTAIN_REGIMEN_POSTPARTUM` |
| Postpartum Follow-Up — BP No Longer High | Prior hypertensive encounter; postpartum, clinic 130/80 | `T12_END_MAINTAIN_REGIMEN_POSTPARTUM` |

## Longitudinal follow-up matrix

Open **Patient Simulator → Preset Patient → Pregnancy Follow-Up Sequence**.

All four Bundles use Patient `PGF001` and episode `pregnancy-demo-001`. Each later Bundle contains
the complete history rather than only the newest reading.

| Preset | Encounters | Follow-up number | Expected result |
|---|---:|---:|---|
| Pregnancy Episode — Initial Visit | 1 | 0 | Mild/moderate gestational HTN; refer |
| Pregnancy Episode — Follow-Up 1 | 2 | 1 | Pregnancy target achieved; maintain |
| Pregnancy Episode — Follow-Up 2 | 3 | 2 | Pregnancy target achieved; maintain |
| Pregnancy Episode — Follow-Up 3 Postpartum (Minimum Complete) | 4 | 3 | Breastfeeding postpartum branch; minimum complete |

The declared follow-up number must always equal the number of prior Encounters:

```text
pregnancy_follow_up_number = Encounter count - 1
```

Follow-up 3 therefore returns:

```json
{
  "episode_id": "pregnancy-demo-001",
  "encounter_count": 4,
  "follow_up_number": 3,
  "phase": "FOLLOW_UP_3",
  "minimum_follow_ups_required": 3,
  "minimum_follow_ups_completed": true,
  "next_follow_up_number": 4,
  "next_follow_up_required": true
}
```

## Test with automatic traversal

1. Start the backend and frontend.
2. Open the Patient Simulator.
3. Choose a preset from either pregnancy group.
4. Keep **Start Tree** set to **Hypertension Diagnosis** (Tree 1).
5. Click **Start Traversal**.
6. For a single-visit preset, confirm that the canvas enters Tree 1 and follows its pregnancy
   link into Tree 12. For a longitudinal pregnancy follow-up, confirm that the current traversal
   starts at the appropriate Tree 12 assessment or status node after previous-visit inference.
7. In the result dialog, expand **Full decision path**.
8. Compare the final node with the matrix above.
9. For a longitudinal preset, also verify the **Pregnancy follow-up episode** section.

Tree 1 treats either `is_pregnant=true` or `is_postpartum=true` as a pregnancy-related episode
while replaying the previous visit. After pregnancy follow-up is inferred, the current encounter
starts in Tree 12. Postpartum follow-up resumes at `T12_C_POSTPARTUM`; a currently normotensive,
high-risk pregnancy resumes at `T12_C_CURRENTLY_PREGNANT`. Acute hypertensive pregnancy
follow-up restarts at Tree 12 START for complete reclassification.

## Test with manual traversal

1. Select the same preset used for the automatic test.
2. Keep the relevant pregnancy tree visible on the canvas.
3. Click **Manual Traverse**.
4. Click the canvas to reveal one entered node at a time.
5. Continue until the result dialog opens.
6. Verify the same expected terminal as the automatic run.

Manual mode uses the same `/evaluate` result as automatic mode and reveals its traversal log step
by step. The backend—not the visible canvas selection—chooses the initial or follow-up entry from
the FHIR encounter history. Therefore, the clinical path and terminal must match.

## Important Tree 12 precedence rules

Tree 12 START has exactly three branches:

1. home BP high;
2. clinic BP high;
3. clinic BP normal.

Postpartum and normotensive high-risk pregnancy are follow-up status branches, not START
shortcuts. The evaluator reaches them only after it replays the immediately previous Encounter
and infers `PREGNANCY_FOLLOW_UP`.

After a high-BP entry, classification precedence is:

1. chronic hypertension;
2. eclampsia severe signs;
3. HELLP;
4. preeclampsia by proteinuria/ACR;
5. preeclampsia by risk factor;
6. gestational hypertension.

This evaluates specific severe diagnoses before the broad gestational-hypertension condition.
Changing that order can silently divert eclampsia, HELLP, or preeclampsia presets into the generic
gestational branch.

## Regenerate and verify

Regenerate the JSON Bundles:

```powershell
uv run python scripts/generate_pregnancy_fhir_presets.py
```

Apply the database schema and authoritative seed:

```powershell
uv run alembic upgrade head
cmd /c "docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U cdss -d cdss < backups\seed.sql"
```

Run focused pregnancy validation:

```powershell
uv run pytest tests/db/test_pregnancy_fhir_presets.py -q
corepack pnpm --dir frontend exec vitest run src/panels/mockPatientForm/fhirBundle.test.ts
```

The backend test verifies:

- official FHIR R4 schema compliance;
- exact expected nodes in automatic evaluation;
- the same expected nodes in manual trace replay;
- coverage of all seven Tree 12 terminals;
- execution coverage of every reachable non-global Tree 12 node.
