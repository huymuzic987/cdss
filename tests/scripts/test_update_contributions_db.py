"""Tests for deployment contribution SQL generation."""

import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

from cdss.infrastructure.git_contributions import (
    CommitRecord,
    GitHistorySnapshot,
)

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "update_contributions_db.py"
generate_sql = cast(
    Callable[[GitHistorySnapshot], str],
    runpy.run_path(str(SCRIPT_PATH))["generate_sql"],
)


def _snapshot() -> GitHistorySnapshot:
    return GitHistorySnapshot(
        contributors={
            "huy": {
                "member_key": "huy",
                "display_name": "Huy",
                "canonical_email": "huymuzic987",
                "commit_count": 2,
                "lines_added": 14,
                "lines_deleted": 3,
                "last_hash": "abc1234",
            }
        },
        commits=(
            CommitRecord(
                hash="abc1234",
                author="Huy",
                message="feat: add history",
                timestamp=1782691200,
                member_keys=("huy", "quang_minh"),
            ),
            CommitRecord(
                hash="def5678",
                author="Huy",
                message="fix: don't guess",
                timestamp=1782777600,
                member_keys=("huy",),
            ),
        ),
    )


def test_generate_sql_atomically_replaces_complete_commit_history() -> None:
    sql = generate_sql(_snapshot())

    assert sql.startswith("-- Auto-generated Git Contribution Statistics SQL Sync\nBEGIN;")
    assert "DELETE FROM public.git_commit_history;" in sql
    assert "'abc1234', 'Huy', 'feat: add history', 1782691200" in sql
    assert "'def5678', 'Huy', 'fix: don''t guess', 1782777600" in sql
    assert "'[\"huy\", \"quang_minh\"]'::jsonb" in sql
    assert sql.rstrip().endswith("COMMIT;")


def test_generate_sql_fails_closed_for_empty_history() -> None:
    assert generate_sql(GitHistorySnapshot(contributors={}, commits=())) == ""
