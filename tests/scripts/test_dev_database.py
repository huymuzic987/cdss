import runpy
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

import psycopg2
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "dev_database.py"
SCRIPT_EXPORTS = runpy.run_path(str(SCRIPT_PATH))

resolve_database_url = cast(
    Callable[[Mapping[str, str], Path], str], SCRIPT_EXPORTS["resolve_database_url"]
)
safe_database_target = cast(Callable[[str], str], SCRIPT_EXPORTS["safe_database_target"])
wait_for_database = cast(Callable[..., None], SCRIPT_EXPORTS["wait_for_database"])
DevDatabaseUnavailable = cast(type[Exception], SCRIPT_EXPORTS["DevDatabaseUnavailable"])


def test_explicit_database_url_wins_over_dotenv(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://dotenv/db\n", encoding="utf-8")

    assert (
        resolve_database_url({"DATABASE_URL": "postgresql://explicit/db"}, env_file)
        == "postgresql://explicit/db"
    )


def test_dotenv_database_url_wins_over_compose_fallback(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://dotenv/db\n", encoding="utf-8")

    assert resolve_database_url({}, env_file) == "postgresql://dotenv/db"


def test_local_compose_database_is_the_final_fallback(tmp_path: Path) -> None:
    assert resolve_database_url({}, tmp_path / "missing.env") == (
        "postgresql://cdss:cdss@127.0.0.1:54321/cdss"
    )


def test_safe_database_target_excludes_credentials() -> None:
    assert (
        safe_database_target("postgresql://user:secret@127.0.0.1:54321/cdss")
        == "127.0.0.1:54321/cdss"
    )


def test_wait_for_database_stops_after_bounded_attempts() -> None:
    attempts = 0
    sleeps: list[float] = []

    def unavailable(_url: str):
        nonlocal attempts
        attempts += 1
        raise psycopg2.OperationalError("unavailable")

    with pytest.raises(DevDatabaseUnavailable) as exc_info:
        wait_for_database(
            "postgresql://user:secret@127.0.0.1:54321/cdss",
            attempts=3,
            delay_seconds=0.25,
            connect=unavailable,
            sleep=sleeps.append,
        )

    assert attempts == 3
    assert sleeps == [0.25, 0.25]
    assert str(exc_info.value) == (
        "Could not connect to PostgreSQL at 127.0.0.1:54321/cdss after 3 attempts."
    )
    assert "secret" not in str(exc_info.value)


def test_wait_for_database_closes_the_successful_connection() -> None:
    class Connection:
        closed = False

        def close(self) -> None:
            self.closed = True

    connection = Connection()

    wait_for_database(
        "postgresql://127.0.0.1:54321/cdss",
        connect=lambda _url: connection,
        sleep=lambda _delay: None,
    )

    assert connection.closed
