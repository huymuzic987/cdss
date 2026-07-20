"""Application settings.

Settings are loaded from environment variables (and an optional ``.env`` file).
``CDSS_MAX_STEPS`` configures the traversal safety limit used by the API.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    development = "development"
    test = "test"
    production = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = Field(default=AppEnv.development)
    # DATABASE_URL is intentionally required and comes from the environment only.
    database_url: str = Field()
    cdss_max_steps: int = Field(default=300, gt=0)
    # Opt-in process-level caching of immutable tree graphs. Off by default:
    # a deployment that enables it owns cache invalidation after any re-seed.
    cdss_graph_cache_enabled: bool = Field(default=False)
    # Opt-in process-level caching of the medicine reference catalog. Same
    # off-by-default/invalidation-on-re-seed tradeoff as cdss_graph_cache_enabled.
    cdss_medicine_cache_enabled: bool = Field(default=False)
    # None means "not explicitly configured" -> resolved from app_env below.
    dev_runtime_logging_enabled: bool | None = Field(default=None)

    @model_validator(mode="after")
    def _resolve_dev_runtime_logging(self) -> Settings:
        if self.dev_runtime_logging_enabled is None:
            # Default to on only for development/test. Production must never
            # enable full-payload runtime logging by default.
            self.dev_runtime_logging_enabled = self.app_env in (
                AppEnv.development,
                AppEnv.test,
            )
        return self


@lru_cache
def get_settings() -> Settings:
    # Fields are populated from the environment; pyright cannot see that here.
    return Settings()  # type: ignore[call-arg]
