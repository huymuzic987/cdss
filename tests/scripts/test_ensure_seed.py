import runpy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import psycopg2
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ensure_seed.py"
SCRIPT_EXPORTS = runpy.run_path(str(SCRIPT_PATH))

seed_transaction_body = cast(Callable[[str], str], SCRIPT_EXPORTS["seed_transaction_body"])
apply_seed_snapshot = cast(Callable[..., None], SCRIPT_EXPORTS["apply_seed_snapshot"])
main = cast(Callable[[], None], SCRIPT_EXPORTS["main"])

EXPECTED_GRAPH_REFRESH = """
DELETE FROM public.node_source_references;
DELETE FROM public.decision_edges;
DELETE FROM public.tree_layouts;
DELETE FROM public.decision_nodes;
DELETE FROM public.decision_trees;
""".strip()


class RecordingCursor:
    def __init__(self, fail_on_statement: int | None = None) -> None:
        self.executed: list[tuple[str, tuple[str, ...] | None]] = []
        self.fail_on_statement = fail_on_statement
        self.closed = False

    def execute(self, statement: str, parameters: tuple[str, ...] | None = None) -> None:
        if self.fail_on_statement == len(self.executed) + 1:
            raise psycopg2.DatabaseError("seed statement failed")
        self.executed.append((statement, parameters))

    def close(self) -> None:
        self.closed = True


class RecordingConnection:
    def __init__(self, fail_on_statement: int | None = None) -> None:
        self.cursor_instance = RecordingCursor(fail_on_statement)
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_seed_transaction_body_removes_only_outer_transaction() -> None:
    sql = "SET client_encoding = 'UTF8';\nBEGIN;\nINSERT INTO x VALUES (1);\nCOMMIT;\n"

    assert (
        seed_transaction_body(sql) == "SET client_encoding = 'UTF8';\nINSERT INTO x VALUES (1);\n"
    )


def test_apply_seed_snapshot_replaces_graph_before_seed_and_metadata() -> None:
    connection = RecordingConnection()

    apply_seed_snapshot(connection, "BEGIN;\nSELECT 'seed';\nCOMMIT;\n", "abc123")

    assert connection.cursor_instance.executed[0] == (EXPECTED_GRAPH_REFRESH, None)
    assert connection.cursor_instance.executed[1] == ("SELECT 'seed';\n", None)
    assert "INSERT INTO _dev_seed_meta" in connection.cursor_instance.executed[2][0]
    assert connection.cursor_instance.executed[2][1] == ("abc123",)
    assert connection.commits == 1
    assert connection.rollbacks == 0
    graph_refresh = connection.cursor_instance.executed[0][0]
    for table in (
        "patients",
        "visits",
        "visit_medications",
        "fhir_import_batches",
        "development_runtime_logs",
        "git_contributions",
        "medicines",
        "symptoms",
        "contraindication_drugs",
    ):
        assert table not in graph_refresh


def test_apply_seed_snapshot_rolls_back_when_seed_fails() -> None:
    connection = RecordingConnection(fail_on_statement=2)

    with pytest.raises(psycopg2.DatabaseError):
        apply_seed_snapshot(connection, "BEGIN;\nSELECT 'seed';\nCOMMIT;\n", "abc123")

    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_main_ends_checksum_transaction_before_migration_and_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seed_path = tmp_path / "backups" / "seed.sql"
    seed_path.parent.mkdir()
    seed_path.write_text("BEGIN;\nSELECT 'seed';\nCOMMIT;\n", encoding="utf-8")
    connection = RecordingConnection()
    events: list[str] = []
    script_globals = main.__globals__

    monkeypatch.setitem(script_globals, "root", tmp_path)
    monkeypatch.setitem(script_globals, "_database_url", lambda: "postgresql://test/cdss")
    monkeypatch.setitem(script_globals, "is_seeded_and_current", lambda _conn, _hash: False)
    monkeypatch.setitem(
        script_globals,
        "apply_seed_snapshot",
        lambda _conn, _sql, _hash: events.append("snapshot"),
    )
    monkeypatch.setattr(script_globals["psycopg2"], "connect", lambda _url: connection)
    monkeypatch.setattr(sys, "argv", ["ensure_seed.py"])

    original_rollback = connection.rollback

    def record_rollback() -> None:
        events.append("rollback")
        original_rollback()

    connection.rollback = record_rollback

    class MigrationResult:
        returncode = 0

    def run_migration(*_args, **_kwargs) -> MigrationResult:
        events.append("migration")
        return MigrationResult()

    monkeypatch.setattr(script_globals["subprocess"], "run", run_migration)

    main()

    assert events == ["rollback", "migration", "snapshot"]
    assert connection.closed
