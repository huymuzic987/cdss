"""Script executed in Jenkins pipeline or standalone to sync Git stats to PostgreSQL."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cdss.infrastructure.git_contributions import (  # noqa: E402
    GitHistorySnapshot,
    parse_git_history_snapshot,
)

# Database Connection Settings
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "54321")
DB_NAME = os.getenv("POSTGRES_DB", "cdss")
DB_USER = os.getenv("POSTGRES_USER", "cdss")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "cdss")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def escape_sql_str(val: str | None) -> str:
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def generate_sql(snapshot: GitHistorySnapshot) -> str:
    """Generate an atomic aggregate and complete-history deployment sync."""
    if not snapshot.contributors or not snapshot.commits:
        return ""
    sql_lines = [
        "-- Auto-generated Git Contribution Statistics SQL Sync",
        "BEGIN;",
    ]
    for data in snapshot.contributors.values():
        total_loc = data["lines_added"] + data["lines_deleted"]
        member_key = escape_sql_str(data["member_key"])
        display_name = escape_sql_str(data["display_name"])
        canonical_email = escape_sql_str(data["canonical_email"])
        commit_count = int(data["commit_count"])
        lines_added = int(data["lines_added"])
        lines_deleted = int(data["lines_deleted"])
        last_hash = escape_sql_str(data.get("last_hash"))

        stmt = f"""INSERT INTO public.git_contributions (
    id, member_key, display_name, canonical_email,
    commit_count, lines_added, lines_deleted, total_loc_changes,
    last_commit_hash, updated_at
) VALUES (
    gen_random_uuid(), {member_key}, {display_name}, {canonical_email},
    {commit_count}, {lines_added}, {lines_deleted}, {total_loc},
    {last_hash}, NOW()
) ON CONFLICT (member_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    canonical_email = EXCLUDED.canonical_email,
    commit_count = EXCLUDED.commit_count,
    lines_added = EXCLUDED.lines_added,
    lines_deleted = EXCLUDED.lines_deleted,
    total_loc_changes = EXCLUDED.total_loc_changes,
    last_commit_hash = EXCLUDED.last_commit_hash,
    updated_at = NOW();"""
        sql_lines.append(stmt)
    sql_lines.append("DELETE FROM public.git_commit_history;")
    for commit in snapshot.commits:
        commit_hash = escape_sql_str(commit.hash)
        author = escape_sql_str(commit.author)
        message = escape_sql_str(commit.message)
        member_keys = escape_sql_str(json.dumps(list(commit.member_keys)))
        sql_lines.append(
            "INSERT INTO public.git_commit_history "
            "(commit_hash, author, message, committed_at, member_keys) VALUES "
            f"({commit_hash}, {author}, {message}, {commit.timestamp}, {member_keys}::jsonb);"
        )
    sql_lines.append("COMMIT;")
    return "\n".join(sql_lines)


def sync_to_db(snapshot: GitHistorySnapshot) -> None:
    if not snapshot.contributors or not snapshot.commits:
        print("No complete Git history parsed; database was not changed.")
        return

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            with conn.begin():
                for data in snapshot.contributors.values():
                    total_loc = data["lines_added"] + data["lines_deleted"]
                    stmt = text(
                        """
                        INSERT INTO public.git_contributions
                            (
                                id,
                                member_key,
                                display_name,
                                canonical_email,
                                commit_count,
                                lines_added,
                                lines_deleted,
                                total_loc_changes,
                                last_commit_hash,
                                updated_at
                            )
                        VALUES (
                            gen_random_uuid(),
                            :member_key,
                            :display_name,
                            :canonical_email,
                            :commit_count,
                            :lines_added,
                            :lines_deleted,
                            :total_loc_changes,
                            :last_commit_hash,
                            NOW()
                        )
                        ON CONFLICT (member_key) DO UPDATE SET
                            display_name = EXCLUDED.display_name,
                            canonical_email = EXCLUDED.canonical_email,
                            commit_count = EXCLUDED.commit_count,
                            lines_added = EXCLUDED.lines_added,
                            lines_deleted = EXCLUDED.lines_deleted,
                            total_loc_changes = EXCLUDED.total_loc_changes,
                            last_commit_hash = EXCLUDED.last_commit_hash,
                            updated_at = NOW();
                    """
                    )
                    conn.execute(
                        stmt,
                        {
                            "member_key": data["member_key"],
                            "display_name": data["display_name"],
                            "canonical_email": data["canonical_email"],
                            "commit_count": data["commit_count"],
                            "lines_added": data["lines_added"],
                            "lines_deleted": data["lines_deleted"],
                            "total_loc_changes": total_loc,
                            "last_commit_hash": data["last_hash"],
                        },
                    )
                conn.execute(text("DELETE FROM public.git_commit_history"))
                insert_commit = text(
                    "INSERT INTO public.git_commit_history "
                    "(commit_hash, author, message, committed_at, member_keys) VALUES "
                    "(:commit_hash, :author, :message, :committed_at, "
                    "CAST(:member_keys AS jsonb))"
                )
                for commit in snapshot.commits:
                    conn.execute(
                        insert_commit,
                        {
                            "commit_hash": commit.hash,
                            "author": commit.author,
                            "message": commit.message,
                            "committed_at": commit.timestamp,
                            "member_keys": json.dumps(list(commit.member_keys)),
                        },
                    )
        print(
            "Successfully synced "
            f"{len(snapshot.contributors)} contributors and {len(snapshot.commits)} commits to DB."
        )
    except Exception as err:
        print(f"Error syncing git stats to database: {err}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync Git stats to database or output SQL")
    parser.add_argument("--print-sql", action="store_true", help="Print SQL statements to stdout")
    parser.add_argument("--scope", default="main", choices=["main", "all"], help="Git log scope")
    args = parser.parse_args()

    snapshot = parse_git_history_snapshot(scope=args.scope)
    if args.print_sql:
        sql = generate_sql(snapshot)
        if not sql:
            print("No complete Git history parsed; refusing to emit sync SQL.", file=sys.stderr)
            raise SystemExit(1)
        print(sql)
    else:
        sync_to_db(snapshot)
