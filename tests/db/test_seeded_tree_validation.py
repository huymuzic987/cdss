"""Read-only validation of the declared first five seeded decision trees."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    "drug-combination",
    "hypertension-type-2-diabetes",
    "hypertension-coronary-artery-disease",
    "hypertension-heart-failure",
    "hypertension-chronic-kidney-disease",
    "hypertension-in-pregnancy",
    "resistant-hypertension",
    "hypertensive-emergency",
]


@pytest.mark.parametrize("tree_key", SEEDED_TREE_KEYS)
def test_seeded_tree_passes_structure_validation(
    seeded_session: Session,
    tree_key: str,
) -> None:
    available_tree_keys = set(seeded_session.execute(select(DecisionTree.tree_key)).scalars())
    if tree_key not in available_tree_keys:
        pytest.skip(f"seeded tree is not available: {tree_key}")

    graph = SqlAlchemyTreeGraphRepository(seeded_session).get_tree(tree_key)
    result = validate_tree_graph(graph, available_tree_keys=available_tree_keys)

    assert result.tree_key == tree_key
