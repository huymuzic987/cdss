"""Smart Database Seed Manager for CDSS Development.

Automatically checks if PostgreSQL database is already seeded with the current version
of backups/seed.sql. If up-to-date, skips expensive SQL execution. If missing or
outdated (checksum changed), runs Alembic migrations and seeds the database.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

import psycopg2

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backups.dump import _database_url  # noqa: E402

GRAPH_REFRESH_SQL = """
DELETE FROM public.node_source_references;
DELETE FROM public.decision_edges;
DELETE FROM public.tree_layouts;
DELETE FROM public.decision_nodes;
DELETE FROM public.decision_trees;
""".strip()


def get_seed_hash(seed_path: Path) -> str:
    """Compute SHA256 checksum of the seed.sql file."""
    hasher = hashlib.sha256()
    with seed_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_seeded_and_current(conn, seed_hash: str) -> bool:
    """Check if PostgreSQL has the tracking table, populated tables, and matching seed hash."""
    cur = conn.cursor()
    try:
        # 1. Check if tracking table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = '_dev_seed_meta'
            );
        """)
        if not cur.fetchone()[0]:
            return False

        # 2. Check if decision_trees table exists and is populated
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'decision_trees'
            );
        """)
        if not cur.fetchone()[0]:
            return False

        cur.execute("SELECT count(*) FROM decision_trees;")
        if cur.fetchone()[0] == 0:
            return False

        # 3. Check if stored hash matches current seed.sql hash
        cur.execute("SELECT hash FROM _dev_seed_meta ORDER BY applied_at DESC LIMIT 1;")
        row = cur.fetchone()
        if row and row[0] == seed_hash:
            return True

        return False
    except Exception:
        return False
    finally:
        cur.close()


def seed_transaction_body(sql_content: str) -> str:
    """Remove the seed dump's outer transaction markers for a managed refresh."""
    lines = sql_content.splitlines(keepends=True)
    begin_indexes = [index for index, line in enumerate(lines) if line.strip() == "BEGIN;"]
    commit_indexes = [index for index, line in enumerate(lines) if line.strip() == "COMMIT;"]

    if len(begin_indexes) != 1 or len(commit_indexes) != 1 or commit_indexes[0] != len(lines) - 1:
        raise ValueError("Seed SQL must contain one BEGIN; and end with one COMMIT;.")

    return "".join(
        line
        for index, line in enumerate(lines)
        if index not in {begin_indexes[0], commit_indexes[0]}
    )


def apply_seed_snapshot(conn, sql_content: str, seed_hash: str) -> None:
    """Atomically replace graph data, apply the seed, and record its checksum."""
    cur = conn.cursor()
    try:
        cur.execute(GRAPH_REFRESH_SQL)
        cur.execute(seed_transaction_body(sql_content))
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS _dev_seed_meta (
                hash TEXT PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO _dev_seed_meta (hash) VALUES (%s)
            ON CONFLICT (hash) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;
            """,
            (seed_hash,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def main():
    force = "--force" in sys.argv or "-f" in sys.argv
    seed_path = root / "backups" / "seed.sql"

    if not seed_path.exists():
        print(f"Error: {seed_path} not found.", file=sys.stderr)
        sys.exit(1)

    seed_hash = get_seed_hash(seed_path)
    conn = psycopg2.connect(_database_url())

    try:
        if not force:
            if is_seeded_and_current(conn, seed_hash):
                print("-> Database is up-to-date with backups/seed.sql (Skipping seed).")
                return

            # Finish the read-only checksum transaction before Alembic changes the schema.
            conn.rollback()

        print(
            "-> Seed is missing or backups/seed.sql was modified. "
            "Applying Alembic migrations and seed..."
        )

        # Run Alembic migrations
        result = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=root)
        if result.returncode != 0:
            print(
                "Alembic upgrade failed (likely orphaned revision). Stamping head...",
                file=sys.stderr,
            )
            subprocess.run(["uv", "run", "alembic", "stamp", "--purge", "head"], cwd=root)
            result = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=root)
            if result.returncode != 0:
                print("Error: Alembic migration failed.", file=sys.stderr)
                sys.exit(1)

        sql_content = seed_path.read_text(encoding="utf-8")
        apply_seed_snapshot(conn, sql_content, seed_hash)
        print("-> Database successfully seeded and tracking hash updated!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
