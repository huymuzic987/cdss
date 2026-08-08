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
SEED_PATH = Path(__file__).resolve().parents[2] / "backups" / "seed.sql"


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
    def __init__(
        self, fail_on_statement: int | None = None, *, fail_on_cursor: bool = False
    ) -> None:
        self.cursor_instance = RecordingCursor(fail_on_statement)
        self.fail_on_cursor = fail_on_cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> RecordingCursor:
        if self.fail_on_cursor:
            raise psycopg2.DatabaseError("cursor creation failed")
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
    sql_content = SEED_PATH.read_text(encoding="utf-8")

    apply_seed_snapshot(connection, sql_content, "abc123")

    assert connection.cursor_instance.executed[0] == (EXPECTED_GRAPH_REFRESH, None)
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
    refresh_payload = connection.cursor_instance.executed[1][0]
    assert "INSERT INTO public.decision_trees" in refresh_payload
    assert "T14_LINK_ECLAMPSIA_PREECLAMPSIA_HELLP_TO_PREGNANCY_TREE" in refresh_payload
    for catalog_table in ("medicines", "symptoms", "contraindication_drugs"):
        assert f"public.{catalog_table}" not in refresh_payload


def test_apply_seed_snapshot_uses_full_seed_for_a_fresh_database() -> None:
    connection = RecordingConnection()
    sql_content = SEED_PATH.read_text(encoding="utf-8")

    apply_seed_snapshot(connection, sql_content, "abc123", refresh_existing_graph=False)

    assert connection.cursor_instance.executed[0] == (seed_transaction_body(sql_content), None)
    assert "INSERT INTO public.medicines" in connection.cursor_instance.executed[0][0]


def test_apply_seed_snapshot_rolls_back_when_seed_fails() -> None:
    connection = RecordingConnection(fail_on_statement=2)

    with pytest.raises(psycopg2.DatabaseError):
        apply_seed_snapshot(connection, SEED_PATH.read_text(encoding="utf-8"), "abc123")

    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_apply_seed_snapshot_rolls_back_when_cursor_creation_fails() -> None:
    connection = RecordingConnection(fail_on_cursor=True)

    with pytest.raises(psycopg2.DatabaseError):
        apply_seed_snapshot(connection, SEED_PATH.read_text(encoding="utf-8"), "abc123")

    assert connection.rollbacks == 1


@pytest.mark.parametrize(
    ("argv", "has_graph", "expected_refresh"),
    [(["ensure_seed.py"], False, False), (["ensure_seed.py", "--force"], True, True)],
)
def test_main_selects_full_or_graph_only_seed_after_migration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list[str],
    has_graph: bool,
    expected_refresh: bool,
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
    monkeypatch.setitem(script_globals, "has_existing_graph", lambda _conn: has_graph)
    monkeypatch.setitem(
        script_globals,
        "apply_seed_snapshot",
        lambda _conn, _sql, _hash, *, refresh_existing_graph: events.append(
            f"snapshot:{refresh_existing_graph}"
        ),
    )
    monkeypatch.setattr(script_globals["psycopg2"], "connect", lambda _url: connection)
    monkeypatch.setattr(sys, "argv", argv)

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

    assert events == ["rollback", "migration", f"snapshot:{expected_refresh}"]
    assert connection.closed
