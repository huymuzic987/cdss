"""Unit tests for team contributions dashboard API endpoint."""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from cdss.api.routes.dashboard_contributions import get_contributions
from cdss.infrastructure.git_contributions import CommitRecord, GitHistorySnapshot
from cdss.main import create_app


class DatabaseMustNotBeQueried:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("Git-backed contribution responses must not query stale aggregates")


def test_get_contributions_endpoint_structure():
    """Verify GET /dashboard/contributions returns valid schema structure."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/dashboard/contributions?scope=main")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"

    data = response.json()
    assert "summary" in data
    assert "contributors" in data
    assert "overlapping_matrix" in data
    assert "recent_commits" in data
    assert data["scope"] == "main"

    summary = data["summary"]
    assert summary["total_commits"] > 0
    assert summary["total_lines_added"] > 0
    assert summary["active_contributors"] >= 5

    contributors = data["contributors"]
    assert len(contributors) >= 5

    # Verify canonical member identities exist
    names = {c["display_name"] for c in contributors}
    assert "Huy" in names
    assert "Quang Minh" in names
    assert "Khoa Dang" in names
    assert "John Tran" in names
    assert "NgPhUyen" in names

    # Verify deliverable list present for members
    for c in contributors:
        assert isinstance(c["deliverables"], list)
        assert len(c["deliverables"]) > 0


def test_get_contributions_all_scope():
    """Verify scope=all returns 200 OK."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/dashboard/contributions?scope=all")
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "all"


def test_contributions_uses_one_git_snapshot_for_totals_history_and_recent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commits = tuple(
        CommitRecord(
            hash=f"hash{i}",
            author="Huy",
            message=f"fix: commit {i}",
            timestamp=100 - i,
            member_keys=("huy",),
        )
        for i in range(6)
    )
    snapshot = GitHistorySnapshot(
        contributors={
            "huy": {
                "member_key": "huy",
                "display_name": "Huy",
                "canonical_email": "huymuzic987",
                "commit_count": 6,
                "lines_added": 12,
                "lines_deleted": 3,
                "last_hash": "hash0",
            }
        },
        commits=commits,
    )
    monkeypatch.setattr(
        "cdss.api.routes.dashboard_contributions.parse_git_history_snapshot",
        lambda scope: snapshot,
    )

    response = get_contributions(
        db=cast(Any, DatabaseMustNotBeQueried()),
        scope="main",
    )

    assert response.summary.total_commits == 6
    assert [item.hash for item in response.commit_history] == [f"hash{i}" for i in range(6)]
    assert [item.hash for item in response.recent_commits] == [f"hash{i}" for i in range(5)]
    assert response.commit_history[0].member_keys == ["huy"]
