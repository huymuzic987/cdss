"""Test-only safety helpers shipped with the project test harness."""

from cdss.testing.database import (
    DatabaseIdentity,
    TestDatabaseEnvironment,
    TestDatabaseSafetyError,
    TestDatabaseTarget,
    assert_destructive_test_database_safe,
    assert_test_database_configuration,
    assert_test_database_connection,
    load_test_database_environment,
    normalize_database_identity,
)

__all__ = [
    "DatabaseIdentity",
    "TestDatabaseEnvironment",
    "TestDatabaseSafetyError",
    "TestDatabaseTarget",
    "assert_destructive_test_database_safe",
    "assert_test_database_connection",
    "assert_test_database_configuration",
    "load_test_database_environment",
    "normalize_database_identity",
]
