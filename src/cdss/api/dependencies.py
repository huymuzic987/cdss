"""FastAPI dependency constructors for CDSS services."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from cdss.core.config import Settings, get_settings
from cdss.core.database import get_db
from cdss.domain.decision_tree import TreeGraphRepository
from cdss.infrastructure.db.caching_repository import (
    CachingTreeGraphRepository,
    get_graph_cache,
)
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository


def get_tree_graph_repository(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TreeGraphRepository:
    repository: TreeGraphRepository = SqlAlchemyTreeGraphRepository(session)
    if settings.cdss_graph_cache_enabled:
        repository = CachingTreeGraphRepository(repository, get_graph_cache())
    return repository
