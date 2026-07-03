# Database backups

Self-contained SQL snapshots of the CDSS database (schema + data), for
disaster recovery and point-in-time reference.

## Contents

- `dump.py` — read-only backup generator. Reconstructs exact DDL (enum,
  tables, constraints, indexes) from `pg_catalog` and emits native `COPY`
  data blocks. Never writes credentials into the output.
- `restore.py` — loads a snapshot into a **local** database, wiping it first.
- `cdss_prod_<UTC-date>.sql` — a generated snapshot. Each file has a header
  with the source database, server version, generation time, and row counts.

The dump captures the five decision-tree tables plus `alembic_version`. It
contains clinical decision-tree definitions only — no patient/PHI data.

## Create a new backup

Reads `DATABASE_URL` from the environment (falling back to `.env`), the same
way the app loads it:

```bash
uv run python backups/dump.py                      # -> backups/cdss_prod_<UTC-date>.sql
uv run python backups/dump.py path/to/backup.sql   # explicit output path
```

The operation is strictly read-only (`SET SESSION read only`).

## Restore

The dump is a complete, ordered SQL script (types → tables → constraints →
indexes → data) wrapped in a single transaction. Restore into an **empty**
database:

```bash
createdb cdss_restore
psql -d cdss_restore -f backups/cdss_prod_<date>.sql
```

The restored database lands on the same Alembic revision as the source
(`alembic_version` is included), so `alembic current` will match and further
migrations apply cleanly.

## Refresh the local database from a snapshot

`restore.py` wipes the target's `public` schema and replays a snapshot
(DDL + data). It is **fail-closed**: the target host must be local
(`localhost`/`127.0.0.1`/`postgres`), so it can never wipe a remote/production
database.

```bash
uv run python backups/restore.py                                  # latest snapshot -> local cdss
uv run python backups/restore.py --dump backups/cdss_prod_<date>.sql
uv run python backups/restore.py --target postgresql://cdss:cdss@localhost:5432/cdss
```
