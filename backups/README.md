# Database Backups & Seed Data

Self-contained SQL snapshots and seed scripts for the CDSS database.

## Contents

The backup artifacts include the static drug contraindication catalog sourced
from `contraindication_drugs_vnha_2022.csv`.

- `backup.sql` — full self-contained snapshot (DDL schema + data) for the decision trees and medicine reference catalog.
- `seed.sql` — data-only seed SQL (inserts, updates, and targeted deletes; no
  schema DDL). It populates a database initialized by `uv run alembic upgrade
  head` and is the authoritative decision-tree graph snapshot.
- `contraindication_drugs_vnha_2022.csv` — source rows for the `contraindication_drugs` catalog.
- `dump.py` — read-only backup generator script.
- `restore.py` — restores a snapshot into a local PostgreSQL database.

## Usage Workflows

### Workflow A: Pure Alembic + Seed Data (Recommended for Development)
```bash
uv run alembic upgrade head
psql -d cdss -f backups/seed.sql
```

For normal local development, prefer `./dev.sh` or `./dev.ps1` instead of
running these commands manually. The launchers call `scripts/ensure_seed.py`:
it fully seeds a fresh empty database, and when the `seed.sql` checksum changes
on an existing database, it refreshes only the decision-tree graph tables.
Clinical and dashboard data, including patients, visits, imported FHIR data,
runtime logs, contribution data, and the medicines, symptoms, and
contraindication catalogs, are preserved.

### Workflow B: Full Snapshot Restore
```bash
uv run python backups/restore.py --dump backups/backup.sql
```
