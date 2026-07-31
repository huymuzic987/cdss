# Pregnancy Follow-Up Flow: Test Guide

> For the complete 21-preset matrix, strict FHIR R4 structure, branch precedence, and
> automatic/manual test instructions, see
> [Tree 12 Pregnancy Presets — Complete Test Guide](pregnancy_preset_testing.md).

## What was implemented

The pregnancy pathway now treats a canonical FHIR Bundle as one pregnancy episode:

- one Encounter = initial visit;
- two Encounters = follow-up 1;
- three Encounters = follow-up 2;
- four Encounters = follow-up 3 (the required minimum is complete);
- five or more Encounters = continuing follow-up.

The evaluator remains stateless. The client sends the episode history on every request, so
automatic and manual traversal use the same `/evaluate` endpoint and produce the same clinical
result. The latest Encounter is the current visit; the Encounter immediately before it is replayed
to infer the current workflow.

Pregnancy-related postpartum visits also enter Tree 12 from Tree 1. A patient with
`is_postpartum=true` is therefore kept in the pregnancy episode even though
`is_pregnant=false`.

## Included presets

In **Patient Simulator → Preset Patient**, open the **Pregnancy Follow-Up Sequence** group.

| Preset | Encounter count | Expected phase | Main expected result |
|---|---:|---|---|
| Pregnancy Episode — Initial Visit | 1 | `INITIAL` | Initial Tree 1 → Tree 12 assessment |
| Pregnancy Episode — Follow-Up 1 | 2 | `FOLLOW_UP_1` | Pregnancy follow-up inferred; target achieved |
| Pregnancy Episode — Follow-Up 2 | 3 | `FOLLOW_UP_2` | Pregnancy follow-up inferred; continued monitoring |
| Pregnancy Episode — Follow-Up 3 Postpartum (Minimum Complete) | 4 | `FOLLOW_UP_3` | Postpartum Tree 12 branch; minimum complete |

All four presets use patient `pregnancy-follow-up-demo` and episode
`pregnancy-demo-001`. Select and run the presets in order when demonstrating the episode.

## Automatic traversal

1. Start the backend and frontend with the project's normal development command.
2. Open the Patient Simulator.
3. Select one of the four **Pregnancy Follow-Up Sequence** presets.
4. Click **Start Traversal**.
5. The canvas automatically highlights the complete path through Tree 1 and Tree 12.
6. In the result dialog, verify the **Pregnancy follow-up episode** section:
   - episode ID;
   - number of Encounters;
   - initial/follow-up number;
   - progress toward the minimum three follow-ups;
   - next requested follow-up number.
7. For follow-up 3, expand **Full decision path** and verify that the path includes the
   postpartum node and ends with the postpartum regimen recommendation.

Expected follow-up 3 metadata:

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

## Manual traversal

1. Select the same preset.
2. Click **Manual Traverse**.
3. Click the canvas once for each next node.
4. When a link changes the active tree, continue clicking; the active canvas changes from Tree 1
   to Tree 12 automatically.
5. Continue until the result dialog opens.
6. Verify that the episode metadata and final recommendation match automatic traversal for the
   same preset.

Manual mode does not run a different clinical algorithm. It evaluates the same Bundle once and
then reveals its `traversal_log` one entered node at a time.

## API usage

Send a pregnancy episode Bundle to:

```text
POST /evaluate
Content-Type: application/json
```

The Bundle must contain:

- exactly one Patient;
- a stable Patient ID across the episode;
- ordered Encounter resources with unique dates;
- one systolic and one diastolic Observation linked to every current/previous Encounter;
- the current pregnancy or postpartum clinical flags;
- `pregnancy_episode_id` as a CDSS input extension;
- `pregnancy_follow_up_number` as a CDSS input extension.

The follow-up number must equal the number of prior Encounters:

```text
pregnancy_follow_up_number = Encounter count - 1
```

Extension examples:

```json
{
  "url": "http://cdss.local/fhir/StructureDefinition/input/pregnancy_episode_id",
  "valueString": "pregnancy-demo-001"
}
```

```json
{
  "url": "http://cdss.local/fhir/StructureDefinition/input/pregnancy_follow_up_number",
  "valueInteger": 3
}
```

A mismatched, negative, or non-integer follow-up number returns HTTP 422 rather than silently
accepting inconsistent episode history.

## Continuing after follow-up 3

To test follow-up 4 or later:

1. Copy the follow-up 3 Bundle.
2. Add a new Encounter with a date later than all existing Encounters.
3. Add its linked SBP and DBP Observations.
4. Update `pregnancy_follow_up_number` to `4`.
5. Update the current pregnancy/postpartum flags and current laboratory values.
6. Send the complete Bundle to `/evaluate`.

The response phase becomes `CONTINUING`, while `minimum_follow_ups_completed` remains `true`.

## Database and verification commands

Apply migrations and the authoritative seed:

```powershell
uv run alembic upgrade head
cmd /c "docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U cdss -d cdss < backups\seed.sql"
```

Run the backend and frontend checks:

```powershell
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```

Database-backed tests require the dedicated `.env.test` configuration and `cdss_test` /
`cdss_schema_test` databases described in `.env.test.example`. Never point those tests at the
development or production database.
