"""Read-only validation of the declared first five seeded decision trees."""

from collections.abc import Generator

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cdss.core.config import get_settings
from cdss.domain.decision_tree import validate_tree_graph
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository
from cdss.infrastructure.db.models import DecisionTree

pytestmark = pytest.mark.database

SEEDED_TREE_KEYS = [
    "hypertension-diagnosis",
    "risk-classification",
    "treatment-threshold-and-bp-target",
    "essential-treatment-strategy",
    "optimal-treatment-strategy",
]


@pytest.fixture(scope="module")
def session() -> Generator[Session, None, None]:
    try:
        settings = get_settings()
    except ValidationError:
        pytest.skip("DATABASE_URL is not configured")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db_session:
            try:
                db_session.execute(select(DecisionTree.id).limit(1)).all()
            except SQLAlchemyError as exc:
                pytest.skip(f"database not reachable or schema unavailable: {exc}")
            yield db_session
    finally:
        engine.dispose()


@pytest.mark.parametrize("tree_key", SEEDED_TREE_KEYS)
def test_seeded_tree_passes_structure_validation(session: Session, tree_key: str) -> None:
    available_tree_keys = set(session.execute(select(DecisionTree.tree_key)).scalars())
    if tree_key not in available_tree_keys:
        pytest.skip(f"seeded tree is not available: {tree_key}")

    graph = SqlAlchemyTreeGraphRepository(session).get_tree(tree_key)
    result = validate_tree_graph(graph, available_tree_keys=available_tree_keys)

    assert result.tree_key == tree_key
