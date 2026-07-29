# Open Questions

Things found while writing the docs in this pass that are ambiguous,
unverifiable from the code alone, or worth a deliberate decision rather than
a silent fix. None of these blocked the documentation work; each is noted
where relevant in the actual docs, and repeated here as a single punch list.

## Real findings (not just documentation gaps)

1. **`context.treatment_preferences.*` keys were added to seeded trees
   without ever being added to `docs/cdss/context-contract.md` first.**
   `combination_options`, `escalation_options`, `additional_drug_classes`,
   and `dose_strategy` are written by `drug-combination`,
   `hypertension-type-2-diabetes`, `hypertension-chronic-kidney-disease`, and
   `optimal-treatment-strategy`, but were undocumented until this pass. I
   documented them (context-contract.md §8) as found, from the current seed
   data, but I could not consult whoever authored those trees to confirm the
   value domains are complete (e.g. whether `dose_strategy` has more allowed
   values than the two observed: `LOW_TO_USUAL_DOSE`, `LOW_DOSE`) or whether
   more keys exist that happen not to appear in the current seed rows. If a
   tree author is available, worth a quick confirmation pass against
   `docs/cdss/context-contract.md` §8.

2. **Two declared 404 response models don't match what's actually
   returned.** `GET /fhir/Library/{tree_key}` (when a tree has no `GLOBAL`
   nodes) and `GET /fhir/Patient/{fhir_id}` (when the patient doesn't exist)
   both declare `responses={404: {"model": EvaluationErrorResponse}}` in
   their route decorators but actually raise a plain FastAPI
   `HTTPException`, whose body is `{"detail": "..."}`, not the declared
   shape. Documented as-is in `docs/api.md`. Whether to fix the code (raise
   the typed error) or the OpenAPI declaration (drop the misleading 404
   model) is a real decision I didn't make on your behalf.

3. **`backups/test_case/` (the `real_test_case` dashboard seed source) does
   not exist in this checkout and is not tracked by git.** `POST
   /dashboard/seed?source=real_test_case` will 404 until someone provisions
   that directory. Documented in `docs/operations.md`, but I don't know
   where that data is supposed to come from (a separate secure handoff? a
   different repo?) since nothing in the codebase says.

4. **`b79e1f82c031_create_symptoms_table.py`'s docstring header claims it
   revises `425debaec093`, but its actual `down_revision` in code is
   `4da35a974155`.** The code is authoritative and migrations run correctly
   in the true order, but the stale docstring could mislead someone reading
   migration history by hand. Noted in `docs/database.md`; not fixed in the
   migration file itself since that's a code change, not a docs change.

5. **`frontend/src/panels/TreeNavigator.tsx` is dead code.** Not imported
   anywhere outside its own file; the top tab bar in `App.tsx` is what
   actually drives tree selection. Left in place and just noted in
   `docs/frontend.md`, per this project's own "don't delete pre-existing
   dead code unless asked" convention (`CLAUDE.md`).

6. **`.env.prod.example` documents `APP_PORT=3000` as the default, but the
   actual Jenkins pipeline hardcodes `APP_PORT=3001`** (with a comment that
   port 3000 is taken by another project on the deploy host). Both are
   accurately reported in `docs/deployment.md`; I didn't change either file,
   since I can't verify what the *currently live* production `.env`
   actually has set (it's a Jenkins secret, not in this repository).

## Things I could not verify from the code alone

7. **Exact GitHub authentication setup for this private repository.** I
   wrote generic HTTPS-PAT / SSH-key troubleshooting guidance into the
   README (based on the remote being `https://github.com/huymuzic987/cdss.git`
   and a commit message referencing an SSH host alias
   `github.com-huymuzic`, implying at least one contributor uses a
   multi-account SSH setup), but I have no way to confirm what
   authentication method your team actually standardizes on, or whether
   there's an org-specific SSO/SAML step. Treat that troubleshooting entry
   as a reasonable default, not a confirmed procedure.

8. **Whether graph/medicine caching (`CDSS_GRAPH_CACHE_ENABLED`,
   `CDSS_MEDICINE_CACHE_ENABLED`) is turned on anywhere in production.**
   Neither flag appears in `.env.prod.example`, so it defaults to off
   (correctness-safe), but I have no visibility into the actual deployed
   `.env` (a Jenkins secret) to confirm.

9. **The `symptoms` table's future consumer.** It's fully migrated and
   seeded but read by no current route or by the traversal engine. I
   documented it as "reference data seeded for future use" based on its
   docstring and lack of any FK relationships, but I don't know what it's
   actually for.

## Stale docs I updated, listed for visibility

These were genuinely wrong before this pass and are now fixed, listed here
so the scope of drift is visible in one place rather than only as scattered
diffs:

- The old README's backup instructions said to run `dump.py` then
  `restore.py` to seed a fresh local database. `dump.py` reads from
  whatever `DATABASE_URL` already points at (your own local database in a
  normal setup), not from production, so that sequence could never actually
  seed an empty database. Fixed (see README and `docs/operations.md`).
- `docs/cdss/traversal-engine-contract.md` and `context-contract.md` both
  described a 5-table schema and 5 seeded trees; the schema is now 14
  tables and the seed is 14 trees (13 traversable, 1 intentionally
  unseeded). Both documents are updated with a dated audit note rather than
  silently rewritten, so the history of what changed and when stays
  visible.
- `docs/cdss/tree-json-dialect.md` was renamed to `docs/cdss/json-dialect.md`
  (git-tracked rename) per the requested deliverable path, and its counts
  were refreshed against the current seed.
- `frontend/README.md` was **not** rewritten in this pass (out of the
  requested scope, which asked for `docs/frontend.md`), but it is now
  measurably stale against the current `frontend/src/` structure (see
  `docs/frontend.md`'s closing section for the specific list). Worth a
  follow-up pass if `frontend/README.md` is meant to stay authoritative.
