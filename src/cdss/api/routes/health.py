"""Liveness endpoint. Does not require database connectivity."""

from fastapi import APIRouter

from cdss.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "environment": settings.app_env.value}
