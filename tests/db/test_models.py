"""ORM-level tests. These inspect mappings/metadata and build transient
instances; none of them require a running database."""

from typing import cast

from sqlalchemy import CheckConstraint, Table, UniqueConstraint
from sqlalchemy import inspect as sa_inspect

from cdss.infrastructure.db.base import Base
from cdss.infrastructure.db.models import (
    DecisionEdge,
    DecisionNode,
    DecisionTree,
    DevelopmentRuntimeLog,
    NodeSourceReference,
    NodeType,
)


def test_node_type_enum_values() -> None:
    assert [member.value for member in NodeType] == [
        "START",
        "CONDITION",
        "INFERENCE",
        "ACTION",
        "END",
        "LINK",
        "GLOBAL",
    ]


def test_table_names() -> None:
    assert set(Base.metadata.tables) == {
        "decision_trees",
        "decision_nodes",
        "decision_edges",
        "node_source_references",
        "development_runtime_logs",
    }


def _table(model: type) -> Table:
    return cast(Table, model.__table__)


def _unique_constraint_names(model: type) -> set[str]:
    return {
        c.name
        for c in _table(model).constraints
        if isinstance(c, UniqueConstraint) and isinstance(c.name, str)
    }


def test_declared_unique_constraints() -> None:
    assert "uq_decision_nodes_tree_id_node_key" in _unique_constraint_names(DecisionNode)
    edge_uniques = _unique_constraint_names(DecisionEdge)
    assert "uq_decision_edges_from_to" in edge_uniques
    assert "uq_decision_edges_from_traversal_order" in edge_uniques
    assert "uq_node_source_references_node_id_reference_order" in _unique_constraint_names(
        NodeSourceReference
    )
    # tree_key / name_en / name_vi are column-level uniques.
    tree_unique_cols = {
        tuple(col.name for col in c.columns)
        for c in _table(DecisionTree).constraints
        if isinstance(c, UniqueConstraint)
    }
    assert {("tree_key",), ("name_en",), ("name_vi",)} <= tree_unique_cols


def test_log_environment_check_constraint() -> None:
    checks = [
        c for c in _table(DevelopmentRuntimeLog).constraints if isinstance(c, CheckConstraint)
    ]
    assert any(c.name == "ck_development_runtime_logs_environment" for c in checks)
    sqltext = " ".join(str(c.sqltext) for c in checks)
    assert "environment" in sqltext
    assert "development" in sqltext and "test" in sqltext


def test_relationship_mappings() -> None:
    assert set(sa_inspect(DecisionTree).relationships.keys()) == {"nodes"}
    assert set(sa_inspect(DecisionNode).relationships.keys()) == {
        "tree",
        "outgoing_edges",
        "incoming_edges",
        "source_references",
    }
    assert set(sa_inspect(DecisionEdge).relationships.keys()) == {"from_node", "to_node"}
    assert set(sa_inspect(NodeSourceReference).relationships.keys()) == {"decision_node"}


def test_edge_foreign_key_disambiguation() -> None:
    # Configuring these relationships proves from_node/to_node resolve to the
    # correct columns despite both FKs pointing at decision_nodes.
    rels = sa_inspect(DecisionEdge).relationships
    assert {c.name for c in rels["from_node"].local_columns} == {"from_node_id"}
    assert {c.name for c in rels["to_node"].local_columns} == {"to_node_id"}


def test_jsonb_payload_assignment() -> None:
    node = DecisionNode(
        node_key="n1",
        node_type=NodeType.CONDITION,
        text_en="systolic >= 140?",
        text_vi="tâm thu >= 140?",
        condition_definition={"op": ">=", "field": "sbp", "value": 140},
        action_payload={"recommendation": "lifestyle"},
    )
    condition = node.condition_definition
    assert condition is not None
    assert condition["op"] == ">="
    assert node.action_payload == {"recommendation": "lifestyle"}


def test_source_reference_page_arrays() -> None:
    ref = NodeSourceReference(
        source_title="2024 Hypertension Guideline",
        section_path=["chapter 3", "section 3.2"],
        printed_page_numbers=[10, 11, 12],
        pdf_page_numbers=[42],
    )
    assert ref.printed_page_numbers == [10, 11, 12]
    assert ref.pdf_page_numbers == [42]
    assert ref.section_path == ["chapter 3", "section 3.2"]
