"""FastAPI dependency constructors for CDSS services."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from cdss.core.database import get_db
from cdss.domain.decision_tree import TreeGraphRepository
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository


def get_tree_graph_repository(
    session: Annotated[Session, Depends(get_db)],
) -> TreeGraphRepository:
    return SqlAlchemyTreeGraphRepository(session)
