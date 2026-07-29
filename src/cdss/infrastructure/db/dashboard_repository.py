"""Public repository composed from focused dashboard query responsibilities."""

from sqlalchemy.orm import Session

from cdss.infrastructure.db.dashboard_filters import DashboardFilterMixin
from cdss.infrastructure.db.dashboard_metrics import (
    AGE_BUCKET_ORDER,
    SBP_BUCKET_ORDER,
    OutcomesCounts,
    OverviewCounts,
    VisitNumberAggregate,
)
from cdss.infrastructure.db.dashboard_outcomes import DashboardOutcomesMixin
from cdss.infrastructure.db.dashboard_overview import DashboardOverviewMixin
from cdss.infrastructure.db.dashboard_patients import DashboardPatientsMixin, invalidate_cache

__all__ = [
    "AGE_BUCKET_ORDER",
    "SBP_BUCKET_ORDER",
    "DashboardRepository",
    "OutcomesCounts",
    "OverviewCounts",
    "VisitNumberAggregate",
    "invalidate_cache",
]


class DashboardRepository(
    DashboardOverviewMixin,
    DashboardOutcomesMixin,
    DashboardPatientsMixin,
    DashboardFilterMixin,
):
    def __init__(self, session: Session) -> None:
        self._session = session
