"""Script executed in Jenkins pipeline or standalone to sync Git stats to PostgreSQL."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cdss.infrastructure.git_contributions import parse_git_history  # noqa: E402

# Database Connection Settings
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "54321")
DB_NAME = os.getenv("POSTGRES_DB", "cdss")
DB_USER = os.getenv("POSTGRES_USER", "cdss")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "cdss")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def sync_to_db(authors: dict[str, dict]) -> None:
    if not authors:
        print("No author statistics parsed.")
        return

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            with conn.begin():
                for data in authors.values():
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
        print(f"Successfully synced stats for {len(authors)} contributors to DB.")
    except Exception as err:
        print(f"Error syncing git stats to database: {err}")


if __name__ == "__main__":
    stats = parse_git_history(scope="main")
    sync_to_db(stats)
