import pytest
from pydantic import ValidationError

from cdss.core.config import AppEnv, Settings

_DB_URL = "postgresql://u:p@localhost:54321/db"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tests from any ambient CDSS environment variables."""
    for var in (
        "APP_ENV",
        "DATABASE_URL",
        "CDSS_MAX_STEPS",
        "DEV_RUNTIME_LOGGING_ENABLED",
        "DEBUG_OUTPUT",
    ):
        monkeypatch.delenv(var, raising=False)


def make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {"app_env": "development", "database_url": _DB_URL}
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_development_settings() -> None:
    settings = make_settings(app_env="development")
    assert settings.app_env is AppEnv.development
    assert settings.dev_runtime_logging_enabled is True


def test_test_settings() -> None:
    settings = make_settings(app_env="test")
    assert settings.app_env is AppEnv.test
    assert settings.dev_runtime_logging_enabled is True


def test_production_settings() -> None:
    settings = make_settings(app_env="production")
    assert settings.app_env is AppEnv.production
    # Production must never enable full-payload runtime logging by default.
    assert settings.dev_runtime_logging_enabled is False


def test_dev_runtime_logging_explicit_override_in_production() -> None:
    settings = make_settings(app_env="production", dev_runtime_logging_enabled=True)
    assert settings.dev_runtime_logging_enabled is True


def test_database_url_required() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="development")  # type: ignore[call-arg]


def test_cdss_max_steps_has_default() -> None:
    assert make_settings().cdss_max_steps == 300


def test_debug_output_defaults_to_false() -> None:
    assert make_settings().debug_output is False


def test_debug_output_can_be_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG_OUTPUT", "true")
    assert make_settings().debug_output is True
