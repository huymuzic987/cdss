"""Public dashboard router composed from focused endpoint modules."""

from fastapi import APIRouter

from cdss.api.routes import dashboard_patients, dashboard_seed, dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
router.include_router(dashboard_seed.router)
router.include_router(dashboard_summary.router)
router.include_router(dashboard_patients.router)
