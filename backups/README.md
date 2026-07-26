# Database Backups & Seed Data

Self-contained SQL snapshots and seed scripts for the CDSS database.

## Contents

- `backup.sql` — full self-contained snapshot (DDL schema + data) for 14 clinical decision trees and the 65-drug reference catalog.
- `seed.sql` — pure data seed script (**INSERT statements only**, no schema DDL). Designed to populate an empty database initialized by `uv run alembic upgrade head`.
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
