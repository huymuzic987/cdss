"""Database-required integration test for the schema migration.

Verifies the migration runs base -> head, the expected tables and node enum
exist, and the development_runtime_logs environment check rejects 'production'.
It inserts no clinical data; the only write attempt is a runtime-log row that
the check constraint must reject, and it is rolled back regardless.

The shared test-database preflight and an immediate destructive-action guard
restrict this module to the dedicated local Docker schema-test database.
"""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from cdss.testing.database import (
    TestDatabaseTarget as DatabaseTarget,
)
from cdss.testing.database import (
    assert_destructive_test_database_safe,
)

pytestmark = pytest.mark.database

REQUIRED_TABLES = {
    "decision_trees",
    "decision_nodes",
    "decision_edges",
    "node_source_references",
    "development_runtime_logs",
    "medicines",
    "patients",
    "patient_conditions",
    "visits",
    "visit_observations",
    "visit_medications",
    "fhir_import_batches",
    "tree_layouts",
    "symptoms",
    "contraindication_drugs",
}
ENUM_LABELS = ["START", "CONDITION", "INFERENCE", "ACTION", "END", "LINK", "GLOBAL"]


@pytest.fixture(scope="module")
def alembic_cfg(schema_database_target: DatabaseTarget) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", schema_database_target.database_url)
    return cfg


def test_schema_migrates_base_to_head(
    alembic_cfg: Config,
    schema_database_engine: Engine,
    schema_database_target: DatabaseTarget,
) -> None:
    _guard(schema_database_engine, schema_database_target)
    command.downgrade(alembic_cfg, "base")
    assert not (REQUIRED_TABLES & set(inspect(schema_database_engine).get_table_names()))

    _guard(schema_database_engine, schema_database_target)
    command.upgrade(alembic_cfg, "head")
    assert REQUIRED_TABLES <= set(inspect(schema_database_engine).get_table_names())


def test_node_type_enum_exists(schema_database_engine: Engine) -> None:
    with schema_database_engine.connect() as conn:
        labels = (
            conn.execute(
                text(
                    "select e.enumlabel from pg_enum e "
                    "join pg_type t on t.oid = e.enumtypid "
                    "where t.typname = 'node_type' order by e.enumsortorder"
                )
            )
            .scalars()
            .all()
        )
    assert labels == ENUM_LABELS


def test_environment_constraint_rejects_production(
    schema_database_engine: Engine,
    schema_database_target: DatabaseTarget,
) -> None:
    insert = text(
        "insert into development_runtime_logs "
        "(id, request_id, environment, input_payload, inference_context, journey, created_at) "
        "values (:id, :request_id, 'production', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, now())"
    )
    with schema_database_engine.connect() as conn:
        trans = conn.begin()
        try:
            assert_destructive_test_database_safe(conn, schema_database_target)
            with pytest.raises(IntegrityError):
                conn.execute(insert, {"id": uuid.uuid4(), "request_id": uuid.uuid4()})
        finally:
            trans.rollback()


def _guard(engine: Engine, target: DatabaseTarget) -> None:
    with engine.connect() as connection:
        assert_destructive_test_database_safe(connection, target)
