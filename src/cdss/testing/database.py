"""Fail-closed configuration and identity guards for PostgreSQL tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from sqlalchemy import text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import ArgumentError

DEFAULT_TEST_ENV_FILE = Path(".env.test")
LOCAL_DOCKER_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})
POSTGRES_DEFAULT_PORT = 5432


@dataclass(frozen=True, slots=True)
class DatabaseIdentity:
    host: str
    port: int
    database: str

    def safe_display(self) -> str:
        return f"{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True, slots=True)
class TestDatabaseTarget:
    app_env: str
    allow_destructive_test_db: str | None
    database_url: str
    test_database_url: str
    expected_database_name: str
    protected_database_names: tuple[str, ...] = ()


class TestDatabaseSafetyError(RuntimeError):
    """A test database failed configuration or connected-identity checks."""

    def __init__(self, reasons: list[str], diagnostics: dict[str, str]) -> None:
        self.reasons = tuple(reasons)
        self.diagnostics = dict(diagnostics)
        reason_text = "; ".join(reasons)
        diagnostic_text = ", ".join(f"{key}={value}" for key, value in sorted(diagnostics.items()))
        super().__init__(f"Unsafe test database configuration: {reason_text}. {diagnostic_text}")


class TestDatabaseEnvironment(BaseSettings):
    """Values loaded only from the explicitly selected test environment file."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    app_env: str
    database_url: str
    test_database_url: str
    test_database_name: str
    allow_destructive_test_db: str
    schema_test_database_url: str
    schema_test_database_name: str
    development_database_name: str = "cdss"
    staging_database_name: str = ""
    production_database_name: str = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del settings_cls, env_settings, file_secret_settings
        return init_settings, dotenv_settings

    def seeded_target(self) -> TestDatabaseTarget:
        return TestDatabaseTarget(
            app_env=self.app_env,
            allow_destructive_test_db=self.allow_destructive_test_db,
            database_url=self.database_url,
            test_database_url=self.test_database_url,
            expected_database_name=self.test_database_name,
            protected_database_names=self._protected_database_names(),
        )

    def schema_target(self) -> TestDatabaseTarget:
        return TestDatabaseTarget(
            app_env=self.app_env,
            allow_destructive_test_db=self.allow_destructive_test_db,
            database_url=self.schema_test_database_url,
            test_database_url=self.schema_test_database_url,
            expected_database_name=self.schema_test_database_name,
            protected_database_names=self._protected_database_names(),
        )

    def _protected_database_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in (
                self.development_database_name,
                self.staging_database_name,
                self.production_database_name,
            )
            if name
        )


def load_test_database_environment(
    env_file: Path = DEFAULT_TEST_ENV_FILE,
) -> TestDatabaseEnvironment:
    """Load test settings without falling back to process variables or normal .env."""

    if not env_file.is_file():
        raise TestDatabaseSafetyError(
            ["required test environment file is missing"],
            {
                "APP_ENV": "<missing>",
                "configured_database_name": "<unknown>",
                "actual_database_name": "<not-connected>",
                "configured_test_database_name": "<unknown>",
                "normalized_identity": "<unknown>",
                "test_env_file": str(env_file),
            },
        )
    try:
        return TestDatabaseEnvironment(_env_file=env_file, _env_file_encoding="utf-8")  # type: ignore[call-arg]
    except ValidationError as exc:
        missing_fields = sorted(
            str(error["loc"][0]) for error in exc.errors() if error["type"] == "missing"
        )
        raise TestDatabaseSafetyError(
            [f"invalid test environment file; missing fields: {', '.join(missing_fields)}"],
            {
                "APP_ENV": "<invalid>",
                "configured_database_name": "<unknown>",
                "actual_database_name": "<not-connected>",
                "configured_test_database_name": "<unknown>",
                "normalized_identity": "<unknown>",
                "test_env_file": str(env_file),
            },
        ) from exc


def normalize_database_identity(database_url: str) -> DatabaseIdentity:
    """Normalize a URL to a password-free host, port, and database identity."""

    try:
        url = make_url(database_url)
    except (ArgumentError, TypeError, ValueError) as exc:
        raise TestDatabaseSafetyError(
            ["database URL is invalid"],
            {
                "APP_ENV": "<unknown>",
                "configured_database_name": "<invalid-url>",
                "actual_database_name": "<not-connected>",
                "configured_test_database_name": "<unknown>",
                "normalized_identity": "<invalid-url>",
            },
        ) from exc
    host = (url.host or "").lower().rstrip(".")
    if host in {"127.0.0.1", "::1"}:
        host = "localhost"
    return DatabaseIdentity(
        host=host,
        port=url.port or POSTGRES_DEFAULT_PORT,
        database=(url.database or "").strip(),
    )


def assert_test_database_configuration(target: TestDatabaseTarget) -> DatabaseIdentity:
    """Reject any target that is not the explicit dedicated local Docker database."""

    configured = normalize_database_identity(target.database_url)
    expected = normalize_database_identity(target.test_database_url)
    diagnostics = _diagnostics(target, configured=configured)
    reasons: list[str] = []

    if target.app_env != "test":
        reasons.append("APP_ENV must equal test")
    if target.allow_destructive_test_db != "true":
        reasons.append("ALLOW_DESTRUCTIVE_TEST_DB must equal true")
    if configured != expected:
        reasons.append("DATABASE_URL and TEST_DATABASE_URL identify different targets")
    if configured.database != target.expected_database_name:
        reasons.append("configured database name differs from TEST_DATABASE_NAME")
    if configured.host not in LOCAL_DOCKER_HOSTS:
        reasons.append("database host is not the configured local Docker target")
    if configured.port != POSTGRES_DEFAULT_PORT:
        reasons.append("database port is not the configured local Docker PostgreSQL port")
    if "test" not in configured.database.lower():
        reasons.append("database name is not dedicated to tests")
    if configured.database in set(target.protected_database_names):
        reasons.append("database name matches a protected non-test database")
    if reasons:
        raise TestDatabaseSafetyError(reasons, diagnostics)
    return configured


def assert_test_database_connection(
    connection: Connection,
    target: TestDatabaseTarget,
) -> DatabaseIdentity:
    """Validate configuration and the actual PostgreSQL database identity."""

    identity = assert_test_database_configuration(target)
    actual_database = connection.execute(text("select current_database()")).scalar_one()
    diagnostics = _diagnostics(
        target,
        configured=identity,
        actual_database=str(actual_database),
    )
    if actual_database != target.expected_database_name:
        raise TestDatabaseSafetyError(
            ["actual current_database() differs from TEST_DATABASE_NAME"],
            diagnostics,
        )
    return identity


def assert_destructive_test_database_safe(
    connection: Connection,
    target: TestDatabaseTarget,
) -> DatabaseIdentity:
    """Guard that must run immediately before destructive test database work."""

    return assert_test_database_connection(connection, target)


def _diagnostics(
    target: TestDatabaseTarget,
    *,
    configured: DatabaseIdentity,
    actual_database: str = "<not-connected>",
) -> dict[str, str]:
    return {
        "APP_ENV": target.app_env,
        "configured_database_name": configured.database or "<missing>",
        "actual_database_name": actual_database,
        "configured_test_database_name": target.expected_database_name or "<missing>",
        "normalized_identity": configured.safe_display(),
    }
