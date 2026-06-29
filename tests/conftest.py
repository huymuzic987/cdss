"""Shared fail-closed fixtures for local Docker PostgreSQL tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cdss.infrastructure.db.models import DecisionTree
from cdss.testing.database import (
    TestDatabaseEnvironment,
    TestDatabaseSafetyError,
    TestDatabaseTarget,
    assert_test_database_connection,
    load_test_database_environment,
)

SEEDED_TREE_KEYS = (
    "hypertension-diagnosis",
    "risk-classification",
    "treatment-threshold-and-bp-target",
    "essential-treatment-strategy",
    "optimal-treatment-strategy",
)


@pytest.fixture(scope="session")
def test_database_environment() -> TestDatabaseEnvironment:
    try:
        return load_test_database_environment()
    except TestDatabaseSafetyError as exc:
        pytest.fail(str(exc), pytrace=False)


@pytest.fixture(scope="session")
def seeded_database_target(
    test_database_environment: TestDatabaseEnvironment,
) -> TestDatabaseTarget:
    return test_database_environment.seeded_target()


@pytest.fixture(scope="session")
def schema_database_target(
    test_database_environment: TestDatabaseEnvironment,
) -> TestDatabaseTarget:
    return test_database_environment.schema_target()


def _connected_engine(target: TestDatabaseTarget) -> Generator[Engine, None, None]:
    engine = create_engine(target.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            assert_test_database_connection(connection, target)
        yield engine
    except (SQLAlchemyError, TestDatabaseSafetyError) as exc:
        pytest.fail(
            "Local Docker test database preflight failed. Start service 'postgres', "
            f"create {target.expected_database_name}, and verify .env.test. {exc}",
            pytrace=False,
        )
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def seeded_database_engine(
    seeded_database_target: TestDatabaseTarget,
) -> Generator[Engine, None, None]:
    yield from _connected_engine(seeded_database_target)


@pytest.fixture(scope="session")
def schema_database_engine(
    schema_database_target: TestDatabaseTarget,
) -> Generator[Engine, None, None]:
    yield from _connected_engine(schema_database_target)


@pytest.fixture(scope="module")
def seeded_session(seeded_database_engine: Engine) -> Generator[Session, None, None]:
    with Session(seeded_database_engine) as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        try:
            available = set(session.execute(select(DecisionTree.tree_key)).scalars())
        except SQLAlchemyError as exc:
            pytest.fail(
                "Local Docker seeded test database schema is unavailable. Apply the existing "
                f"Alembic migration before seeding Trees 1-5. {exc}",
                pytrace=False,
            )
        missing = [tree_key for tree_key in SEEDED_TREE_KEYS if tree_key not in available]
        if missing:
            pytest.fail(
                "Local Docker test database is not seeded with Trees 1-5. No reproducible seed "
                "artifact exists in this repository; load the authoritative seed externally. "
                f"Missing tree keys: {', '.join(missing)}",
                pytrace=False,
            )
        yield session
        session.rollback()
