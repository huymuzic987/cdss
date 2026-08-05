# Database Backups & Seed Data

Self-contained SQL snapshots and seed scripts for the CDSS database.

## Contents

The backup artifacts include the static drug contraindication catalog sourced
from `contraindication_drugs_vnha_2022.csv`.

- `backup.sql` — full self-contained snapshot (DDL schema + data) for the decision trees and medicine reference catalog.
- `seed.sql` — pure data seed script (**INSERT statements only**, no schema DDL). Designed to populate an empty database initialized by `uv run alembic upgrade head`.
- `contraindication_drugs_vnha_2022.csv` — source rows for the `contraindication_drugs` catalog.
- `dump.py` — read-only backup generator script.
- `restore.py` — restores a snapshot into a local PostgreSQL database.

## Usage Workflows

### Workflow A: Pure Alembic + Seed Data (Recommended for Development)
```bash
uv run alembic upgrade head
psql -d cdss -f backups/seed.sql
```

### Workflow B: Full Snapshot Restore
```bash
uv run python backups/restore.py --dump backups/backup.sql
```
