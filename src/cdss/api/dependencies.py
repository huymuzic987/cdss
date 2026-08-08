"""FastAPI dependency constructors for CDSS services."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from cdss.core.config import Settings, get_settings
from cdss.core.database import get_db
from cdss.domain.contraindications.contraindication_catalog import ContraindicationDrugRepository
from cdss.domain.decision_tree import MedicineRepository, TreeGraphRepository
from cdss.infrastructure.db.caching_medicine_repository import (
    CachingMedicineRepository,
    get_medicine_catalog_cache,
)
from cdss.infrastructure.db.caching_repository import (
    CachingTreeGraphRepository,
    get_graph_cache,
)
from cdss.infrastructure.db.contraindication_repository import (
    SqlAlchemyContraindicationDrugRepository,
)
from cdss.infrastructure.db.dashboard.dashboard_repository import DashboardRepository
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository
from cdss.infrastructure.db.medicine_repository import SqlAlchemyMedicineRepository
from cdss.infrastructure.db.tree_layout_repository import TreeLayoutRepository


def get_tree_graph_repository(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TreeGraphRepository:
    repository: TreeGraphRepository = SqlAlchemyTreeGraphRepository(session)
    if settings.cdss_graph_cache_enabled:
        repository = CachingTreeGraphRepository(repository, get_graph_cache())
    return repository


def get_medicine_repository(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MedicineRepository:
    repository: MedicineRepository = SqlAlchemyMedicineRepository(session)
    if settings.cdss_medicine_cache_enabled:
        repository = CachingMedicineRepository(repository, get_medicine_catalog_cache())
    return repository


def get_contraindication_repository(
    session: Annotated[Session, Depends(get_db)],
) -> ContraindicationDrugRepository:
    return SqlAlchemyContraindicationDrugRepository(session)


def get_dashboard_repository(session: Annotated[Session, Depends(get_db)]) -> DashboardRepository:
    return DashboardRepository(session)


def get_tree_layout_repository(
    session: Annotated[Session, Depends(get_db)],
) -> TreeLayoutRepository:
    return TreeLayoutRepository(session)
