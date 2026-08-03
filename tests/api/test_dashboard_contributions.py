"""Unit tests for team contributions dashboard API endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cdss.main import create_app


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
