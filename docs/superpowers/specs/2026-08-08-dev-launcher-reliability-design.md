# Development Launcher Reliability Design

## Goal

Make `dev.sh` and `dev.ps1` start the current backend and frontend reliably
from a local checkout, including when no `.env` file exists and when the
checked-in seed has changed since the local database was last seeded.

## Scope

This change covers the Bash and PowerShell development launchers and the
development seed manager they share. It does not change production database
configuration, general backup utilities, application configuration, or the
frontend and backend server commands.

## Database configuration

The launchers preserve the existing configuration precedence:

1. An exported `DATABASE_URL` remains authoritative.
2. If the repository `.env` contains `DATABASE_URL`, the existing Python
   loader continues to use it.
3. If neither source exists, the launcher exports the URL for the local
   PostgreSQL service declared in `compose.yaml` before running readiness,
   migration, seed, or backend commands.

The fallback is launcher-only. Commands such as `backups/dump.py` remain
strict and continue to require `DATABASE_URL` or `.env`, preventing an
unrelated command from silently selecting a local database.

## Readiness and diagnostics

Both launchers use a bounded database readiness loop. Bash will no longer
retry forever. A failed Docker start is recorded separately from a failed
database connection, and the final message identifies the failed connection
and the expected local endpoint instead of assuming that Docker is the only
possible cause.

The launchers continue to start Uvicorn with reload limited to `src` and Vite
from `frontend`. Their existing process cleanup behavior remains unchanged.

## Seed refresh

`backups/seed.sql` is the authoritative snapshot for decision trees and their
graph metadata. A stale checksum can represent the same logical tree or node
with new UUIDs, so inserting by UUID alone is insufficient for an older local
database.

After Alembic reaches `head`, the seed manager refreshes the graph snapshot in
one database transaction by deleting these seeded graph tables in foreign-key
order:

1. `node_source_references`
2. `decision_edges`
3. `tree_layouts`
4. `decision_nodes`
5. `decision_trees`

It then executes `backups/seed.sql` and records the new checksum. This removes
obsolete graph rows and avoids logical-key conflicts caused by changed UUIDs.
The transaction rolls back on any error, including seed or metadata failures.

The refresh does not delete patients, visits, visit medications, FHIR import
history, runtime logs, contribution data, medicines, symptoms, or
contraindication catalogs. Existing medicine rows must remain because visit
medications reference them; their stable `drug_id` values are updated by the
seed's existing upserts.

`--force` and `-ForceSeed` use the same targeted graph refresh. An unchanged
checksum continues to skip migration and seed work unless force is requested.

## Error handling

- Missing or unreachable local PostgreSQL causes a bounded, nonzero launcher
  exit with a clear diagnostic.
- Graph cleanup, seed application, and checksum recording are atomic. Any
  database error preserves the pre-refresh graph data.
- Server processes start only after readiness and seed management succeed.

## Testing

Automated tests will cover:

- Bash and PowerShell launchers defining the same Compose fallback without
  overriding explicit database configuration.
- Bash having a bounded readiness loop and both launchers emitting accurate
  failure diagnostics.
- Seed refresh order and transaction rollback behavior.
- Reseeding a database containing an older UUID for a current logical node,
  while preserving representative non-graph clinical data.
- An unchanged seed checksum skipping refresh work.

The final verification includes Ruff formatting and linting, Pyright, relevant
Pytest tests, PowerShell and Bash parse checks, `git diff --check`, and live
launcher smoke tests for backend and frontend reload behavior when Docker is
available.
