"""Restore a CDSS SQL backup into a LOCAL database (wipes it first).

Reusable counterpart to ``dump.py``. Intended for refreshing the local Docker
database from a production snapshot. It DROPs and recreates the ``public``
schema on the target, then replays the dump (DDL + data).

Fail-closed safety: the target host must be local. The script refuses any
remote host (e.g. Neon/AWS), so it can never wipe production.

Usage (target defaults to the local Docker DB, dump to the latest snapshot):

    uv run python backups/restore.py
    uv run python backups/restore.py --dump backups/cdss_prod_20260701.sql
    uv run python backups/restore.py --target postgresql://cdss:cdss@localhost:5432/cdss
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import psycopg2
from sqlalchemy.engine import make_url

BACKUPS_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET = "postgresql://cdss:cdss@localhost:54321/cdss"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})


def latest_dump() -> Path:
    dumps = sorted(BACKUPS_DIR.glob("cdss_prod_*.sql"))
    if not dumps:
        sys.exit("No cdss_prod_*.sql backup found in backups/.")
    return dumps[-1]


def assert_local_target(url: str) -> str:
    """Refuse anything that is not a local database; return a safe display."""
    u = make_url(url)
    host = (u.host or "").lower().rstrip(".")
    if host not in LOCAL_HOSTS:
        sys.exit(
            f"REFUSING: target host '{host}' is not local. "
            "restore.py only wipes local databases."
        )
    return f"{host}:{u.port or 54321}/{u.database}"


def wipe_and_replay(conn, dump_path: Path) -> None:
    conn.autocommit = True
    cur = conn.cursor()

    # Wipe: drop everything in public, then recreate the empty schema.
    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

    lines = dump_path.read_text(encoding="utf-8").splitlines(keepends=True)
    sql_buf: list[str] = []
    i, n = 0, len(lines)

    def flush_sql() -> None:
        stmt = "".join(sql_buf)
        stmt = "\n".join(
            x for x in stmt.splitlines() if x.strip() not in ("BEGIN;", "COMMIT;")
        )
        has_code = any(
            line.strip() and not line.strip().startswith("--")
            for line in stmt.splitlines()
        )
        if has_code:
            cur.execute(stmt)

    while i < n:
        line = lines[i]
        if line.startswith("COPY ") and line.rstrip().endswith("FROM stdin;"):
            flush_sql()
            sql_buf = []
            copy_sql = line.rstrip()
            i += 1
            data: list[str] = []
            while i < n and lines[i].rstrip("\n") != "\\.":
                data.append(lines[i])
                i += 1
            cur.copy_expert(copy_sql, io.StringIO("".join(data)))
            i += 1  # skip the \. terminator
            continue
        sql_buf.append(line)
        i += 1
    flush_sql()


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a CDSS backup into a local DB.")
    parser.add_argument("--dump", type=Path, default=None, help="Backup .sql (default: latest).")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Local target DATABASE_URL.")
    args = parser.parse_args()

    dump_path = args.dump or latest_dump()
    if not dump_path.is_file():
        sys.exit(f"Dump file not found: {dump_path}")

    display = assert_local_target(args.target)
    print(f"Restoring {dump_path.name} -> {display}")

    conn = psycopg2.connect(args.target)
    try:
        wipe_and_replay(conn, dump_path)
        cur = conn.cursor()
        cur.execute("select tablename from pg_tables where schemaname='public' order by 1")
        tables = [r[0] for r in cur.fetchall()]
        print("Restored row counts:")
        for t in tables:
            cur.execute(f'select count(*) from public."{t}"')
            print(f"  {t}: {cur.fetchone()[0]}")
    finally:
        conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
