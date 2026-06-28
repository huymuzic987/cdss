from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cdss.core.config import get_settings
from cdss.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("APP_ENV", "development")
    # A bogus host/port: /health must answer without ever connecting to it.
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/db")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as test_client:
            yield test_client
    finally:
        get_settings.cache_clear()


def test_health_response(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}


def test_health_works_without_postgres(client: TestClient) -> None:
    # The DATABASE_URL points at a dead port; a passing call proves /health
    # never touches the database.
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
