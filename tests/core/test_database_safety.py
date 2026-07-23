"""Unit tests for the fail-closed destructive database guard."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from sqlalchemy.engine import Connection

from cdss.testing.database import (
    TestDatabaseSafetyError as SafetyError,
)
from cdss.testing.database import (
    TestDatabaseTarget as DatabaseTarget,
)
from cdss.testing.database import (
    assert_destructive_test_database_safe,
    load_test_database_environment,
)

LOCAL_URL = "postgresql://cdss:secret@localhost:54321/cdss_test"


class _ScalarResult:
    def __init__(self, value: str) -> None:
        self._value = value

    def scalar_one(self) -> str:
        return self._value


class _Connection:
    def __init__(self, database_name: str) -> None:
        self.database_name = database_name

    def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self.database_name)


def _target(**changes: object) -> DatabaseTarget:
    values: dict[str, object] = {
        "app_env": "test",
        "allow_destructive_test_db": "true",
        "database_url": LOCAL_URL,
        "test_database_url": "postgresql+psycopg2://cdss:other@127.0.0.1/cdss_test",
        "expected_database_name": "cdss_test",
        "protected_database_names": ("cdss", "staging", "production"),
    }
    values.update(changes)
    return DatabaseTarget(**values)  # type: ignore[arg-type]


def _guard(target: DatabaseTarget, actual_database: str = "cdss_test") -> None:
    connection = cast(Connection, _Connection(actual_database))
    assert_destructive_test_database_safe(connection, target)


@pytest.mark.parametrize("app_env", ["development", "production", "TEST"])
def test_guard_rejects_non_test_environment(app_env: str) -> None:
    with pytest.raises(SafetyError, match="APP_ENV must equal test"):
        _guard(_target(app_env=app_env))


@pytest.mark.parametrize("allow", [None, "", "false", "TRUE"])
def test_guard_rejects_missing_or_false_destructive_opt_in(allow: str | None) -> None:
    with pytest.raises(SafetyError, match="ALLOW_DESTRUCTIVE_TEST_DB"):
        _guard(_target(allow_destructive_test_db=allow))


def test_guard_rejects_different_database_and_test_urls() -> None:
    with pytest.raises(SafetyError, match="identify different targets"):
        _guard(_target(test_database_url="postgresql://cdss:x@localhost:54321/other_test"))


def test_guard_rejects_configured_database_name_mismatch() -> None:
    with pytest.raises(SafetyError, match="differs from TEST_DATABASE_NAME"):
        _guard(_target(expected_database_name="another_test"))


def test_guard_rejects_non_local_target_without_exposing_password() -> None:
    target = _target(
        database_url="postgresql://cdss:super-secret@db.example.com:54321/cdss_test",
        test_database_url="postgresql://cdss:super-secret@db.example.com:54321/cdss_test",
    )

    with pytest.raises(SafetyError) as exc_info:
        _guard(target)

    assert "local Docker" in str(exc_info.value)
    assert "super-secret" not in str(exc_info.value)


def test_guard_rejects_non_configured_port() -> None:
    target = _target(
        database_url="postgresql://cdss:secret@localhost:5432/cdss_test",
        test_database_url="postgresql://cdss:secret@localhost:5432/cdss_test",
    )
    with pytest.raises(
        SafetyError,
        match="database port is not the configured local Docker PostgreSQL port",
    ):
        _guard(target)


def test_guard_rejects_actual_database_name_mismatch() -> None:
    with pytest.raises(SafetyError, match=r"current_database\(\)") as exc_info:
        _guard(_target(), actual_database="cdss")

    assert exc_info.value.diagnostics["actual_database_name"] == "cdss"


def test_guard_rejects_configured_protected_database_name() -> None:
    protected_url = "postgresql://cdss:secret@localhost:54321/cdss"
    with pytest.raises(SafetyError, match="protected non-test database"):
        _guard(
            _target(
                database_url=protected_url,
                test_database_url=protected_url,
                expected_database_name="cdss",
            ),
            actual_database="cdss",
        )


def test_guard_accepts_valid_local_docker_test_database() -> None:
    _guard(_target())


def test_test_environment_loader_fails_closed_when_file_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@cloud.example/prod")

    with pytest.raises(SafetyError, match="required test environment file is missing"):
        load_test_database_environment(tmp_path / "missing.env.test")
