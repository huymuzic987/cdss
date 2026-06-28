"""Database-required integration test for the schema migration.

Verifies the migration runs base -> head, the expected tables and node enum
exist, and the development_runtime_logs environment check rejects 'production'.
It inserts no clinical data; the only write attempt is a runtime-log row that
the check constraint must reject, and it is rolled back regardless.

Skipped automatically when no PostgreSQL database is reachable. Refuses to run
against a production environment because it cycles the schema destructively.
"""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from cdss.core.config import AppEnv, get_settings

pytestmark = pytest.mark.database

REQUIRED_TABLES = {
    "decision_trees",
    "decision_nodes",
    "decision_edges",
    "node_source_references",
    "development_runtime_logs",
}
ENUM_LABELS = ["START", "CONDITION", "INFERENCE", "ACTION", "END", "LINK", "GLOBAL"]


@pytest.fixture(scope="module")
def engine() -> Engine:
    settings = get_settings()
    if settings.app_env is AppEnv.production:
        pytest.skip("refusing to cycle the schema against a production database")
    eng = create_engine(settings.database_url)
    try:
        with eng.connect():
            pass
    except Exception as exc:  # noqa: BLE001 - any connect failure means "no DB available"
        pytest.skip(f"database not reachable: {exc}")
    return eng


@pytest.fixture(scope="module")
def alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    return cfg


def test_schema_migrates_base_to_head(alembic_cfg: Config, engine: Engine) -> None:
    command.downgrade(alembic_cfg, "base")
    assert not (REQUIRED_TABLES & set(inspect(engine).get_table_names()))

    command.upgrade(alembic_cfg, "head")
    assert REQUIRED_TABLES <= set(inspect(engine).get_table_names())


def test_node_type_enum_exists(engine: Engine) -> None:
    with engine.connect() as conn:
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


def test_environment_constraint_rejects_production(engine: Engine) -> None:
    insert = text(
        "insert into development_runtime_logs "
        "(id, request_id, environment, input_payload, inference_context, journey, created_at) "
        "values (:id, :request_id, 'production', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, now())"
    )
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            with pytest.raises(IntegrityError):
                conn.execute(insert, {"id": uuid.uuid4(), "request_id": uuid.uuid4()})
        finally:
            trans.rollback()
