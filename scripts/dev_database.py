from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
LOCAL_COMPOSE_DATABASE_URL = "postgresql://cdss:cdss@127.0.0.1:54321/cdss"


def _dotenv_database_url(env_path: Path) -> str | None:
    if not env_path.is_file():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            value = line.split("=", 1)[1].strip()
            return value or None
    return None


def resolve_database_url(environ: Mapping[str, str], env_path: Path) -> str:
    return (
        environ.get("DATABASE_URL") or _dotenv_database_url(env_path) or LOCAL_COMPOSE_DATABASE_URL
    )


def safe_database_target(database_url: str) -> str:
    parsed = urlsplit(database_url)
    host = parsed.hostname or "<unknown-host>"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "<unknown-database>"
    return f"{host}:{port}/{database}"


class DevDatabaseUnavailable(Exception):
    """Raised when the local PostgreSQL database cannot be reached in time."""


def wait_for_database(
    database_url: str,
    attempts: int = 30,
    delay_seconds: float = 0.5,
    *,
    connect: Callable[[str], Any] = psycopg2.connect,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    for attempt in range(attempts):
        try:
            connection = connect(database_url)
        except psycopg2.OperationalError:
            if attempt < attempts - 1:
                sleep(delay_seconds)
        else:
            connection.close()
            return

    raise DevDatabaseUnavailable(
        f"Could not connect to PostgreSQL at {safe_database_target(database_url)} "
        f"after {attempts} attempts."
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("resolve")
    commands.add_parser("wait")
    args = parser.parse_args(argv)

    if args.command == "resolve":
        print(resolve_database_url(os.environ, ROOT / ".env"))
        return 0

    database_url = os.environ["DATABASE_URL"]
    try:
        wait_for_database(database_url)
    except DevDatabaseUnavailable as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
