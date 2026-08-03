"""Public dashboard router composed from focused endpoint modules."""

from fastapi import APIRouter

from cdss.api.routes import (
    dashboard_contributions,
    dashboard_patients,
    dashboard_seed,
    dashboard_summary,
)

from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
router.include_router(dashboard_seed.router)
router.include_router(dashboard_summary.router)
router.include_router(dashboard_patients.router)
router.include_router(dashboard_contributions.router)


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def dashboard_root_redirect():
    """Redirect GET /dashboard to GET /dashboard/summary."""
    return RedirectResponse(url="/dashboard/summary")


