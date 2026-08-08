# Development Launcher Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make both development launchers use the local Compose database as a safe fallback, fail promptly with accurate diagnostics, and refresh stale graph seed data without deleting clinical development data.

**Architecture:** A small Python development-database helper owns URL precedence, password-free target display, and bounded connection retries; Bash and PowerShell call it before seeding. The seed manager treats the decision-tree graph as an authoritative snapshot, strips the seed file's outer transaction markers, and atomically replaces only graph tables before recording the checksum.

**Tech Stack:** Python 3.12, psycopg2, pytest, Bash, PowerShell 7, Docker Compose, Alembic, Uvicorn, Vite.

## Global Constraints

- `DATABASE_URL` overrides `.env`, and `.env` overrides the local Compose fallback.
- The fallback applies only when launching through `dev.sh` or `dev.ps1`.
- The local fallback target is PostgreSQL at `127.0.0.1:54321`, database `cdss`, matching `compose.yaml`.
- Database error messages must never display usernames or passwords.
- Seed refresh may replace decision-tree graph data but must preserve patients, visits, visit medications, FHIR import history, runtime logs, contribution data, medicines, symptoms, and contraindication catalogs.
- Python files must be formatted with Ruff and pass Ruff, Pyright, and relevant Pytest tests.
- Frontend source files are out of scope; live verification must still prove Vite reload behavior.

---

### Task 1: Development database resolution and readiness helper

**Files:**
- Create: `scripts/dev_database.py`
- Create: `tests/scripts/test_dev_database.py`

**Interfaces:**
- Produces: `resolve_database_url(environ: Mapping[str, str], env_path: Path) -> str`
- Produces: `safe_database_target(database_url: str) -> str`
- Produces: `wait_for_database(database_url: str, attempts: int = 30, delay_seconds: float = 0.5) -> None`
- Produces CLI commands: `python scripts/dev_database.py resolve` and `python scripts/dev_database.py wait`

- [ ] **Step 1: Write failing URL-precedence tests**

Create `tests/scripts/test_dev_database.py` with literal expectations that catch an overridden explicit URL, an ignored `.env`, or a missing Compose fallback:

```python
from pathlib import Path

from scripts.dev_database import resolve_database_url


def test_explicit_database_url_wins_over_dotenv(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://dotenv/db\n", encoding="utf-8")

    assert resolve_database_url(
        {"DATABASE_URL": "postgresql://explicit/db"}, env_file
    ) == "postgresql://explicit/db"


def test_dotenv_database_url_wins_over_compose_fallback(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://dotenv/db\n", encoding="utf-8")

    assert resolve_database_url({}, env_file) == "postgresql://dotenv/db"


def test_local_compose_database_is_the_final_fallback(tmp_path: Path) -> None:
    assert resolve_database_url({}, tmp_path / "missing.env") == (
        "postgresql://cdss:cdss@127.0.0.1:54321/cdss"
    )
```

- [ ] **Step 2: Run the resolver tests and verify RED**

Run: `uv run pytest tests/scripts/test_dev_database.py -q`

Expected: collection fails because `scripts.dev_database` does not exist.

- [ ] **Step 3: Implement minimal URL resolution and safe display**

Create `scripts/dev_database.py` with:

```python
from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
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
        environ.get("DATABASE_URL")
        or _dotenv_database_url(env_path)
        or LOCAL_COMPOSE_DATABASE_URL
    )


def safe_database_target(database_url: str) -> str:
    parsed = urlsplit(database_url)
    host = parsed.hostname or "<unknown-host>"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "<unknown-database>"
    return f"{host}:{port}/{database}"
```

- [ ] **Step 4: Add failing bounded-readiness tests**

Add tests using a connector double only at the external psycopg2 boundary. Assert public behavior: exact attempt count, connections closed on success, no sleep after the last failure, and a password-free exception message.

```python
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
```

- [ ] **Step 5: Run the readiness test and verify RED**

Run: `uv run pytest tests/scripts/test_dev_database.py -q`

Expected: fails because `DevDatabaseUnavailable` and `wait_for_database` are absent.

- [ ] **Step 6: Implement bounded readiness and the CLI**

Add `DevDatabaseUnavailable`, dependency-injected `connect`/`sleep` parameters, and an argparse CLI. `resolve` prints the selected URL for command substitution. `wait` reads the already-exported `DATABASE_URL`, closes the successful psycopg2 connection, and returns exit code 1 with the sanitized error on failure.

- [ ] **Step 7: Verify Task 1 GREEN**

Run: `uv run pytest tests/scripts/test_dev_database.py -q`

Expected: all helper tests pass.

- [ ] **Step 8: Format and commit Task 1**

Run:

```bash
uv run ruff format scripts/dev_database.py tests/scripts/test_dev_database.py
uv run ruff check scripts/dev_database.py tests/scripts/test_dev_database.py
git add scripts/dev_database.py tests/scripts/test_dev_database.py
git commit -m "feat(dev): add bounded local database resolver" -- scripts/dev_database.py tests/scripts/test_dev_database.py
```

---

### Task 2: Wire Bash and PowerShell launchers to the helper

**Files:**
- Modify: `dev.sh`
- Modify: `dev.ps1`
- Create: `tests/scripts/test_dev_launchers.py`

**Interfaces:**
- Consumes: `scripts/dev_database.py resolve`
- Consumes: `scripts/dev_database.py wait`
- Preserves: `./dev.sh --force` and `.\dev.ps1 -ForceSeed`

- [ ] **Step 1: Write failing launcher subprocess tests**

Build a temporary fake `uv` executable that delegates the resolver command to the real Python interpreter, returns a controlled result for the external database wait, records the resulting `DATABASE_URL` for `ensure_seed.py` and Uvicorn, and returns success without starting real servers. Fake Docker and pnpm only at those external process boundaries. Execute the real `dev.sh`; execute the real `dev.ps1` when `pwsh` is installed.

The tests assert these observable outcomes:

```python
def test_bash_launcher_exports_compose_fallback_to_seed_and_backend(...):
    result, recorded_urls = run_launcher("dev.sh", environ={})
    assert result.returncode == 0, result.stderr
    assert recorded_urls == [
        "postgresql://cdss:cdss@127.0.0.1:54321/cdss",
        "postgresql://cdss:cdss@127.0.0.1:54321/cdss",
    ]


def test_bash_launcher_preserves_explicit_database_url(...):
    result, recorded_urls = run_launcher(
        "dev.sh", environ={"DATABASE_URL": "postgresql://explicit/db"}
    )
    assert result.returncode == 0, result.stderr
    assert recorded_urls == ["postgresql://explicit/db", "postgresql://explicit/db"]


def test_powershell_launcher_reports_database_failure_not_docker_failure(...):
    result = run_failing_powershell_launcher()
    assert result.returncode == 1
    assert "Could not connect to PostgreSQL at" in result.stderr
    assert "Make sure Docker Desktop or WSL Docker daemon is running" not in result.stdout
```

- [ ] **Step 2: Run launcher tests and verify RED**

Run: `uv run pytest tests/scripts/test_dev_launchers.py -q`

Expected: fallback tests fail because the current launchers do not resolve/export the Compose URL; the Bash failure case times out at the test harness limit because its retry is unbounded.

- [ ] **Step 3: Update `dev.sh`**

After changing to the repository root, resolve and export the URL:

```bash
if ! DATABASE_URL="$(uv run python scripts/dev_database.py resolve)"; then
    echo "Error: Could not resolve the development database URL." >&2
    exit 1
fi
export DATABASE_URL
```

Retain the Docker/WSL start attempts, remove suppressed unbounded psycopg2 probing, and use:

```bash
if ! uv run python scripts/dev_database.py wait; then
    exit 1
fi
```

- [ ] **Step 4: Update `dev.ps1`**

Resolve the URL before Docker startup, check `$LASTEXITCODE`, trim the captured value, and assign `$env:DATABASE_URL`. Remove `Test-PortOpen` and the duplicate retry loop; call the shared `wait` command and propagate its failure code. Preserve seed arguments, concurrent server startup, and `Stop-Tree`.

- [ ] **Step 5: Verify Task 2 GREEN and parser validity**

Run:

```bash
uv run pytest tests/scripts/test_dev_launchers.py -q
bash -n dev.sh
pwsh -NoLogo -NoProfile -Command '$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path "dev.ps1"), [ref]$tokens, [ref]$errors) > $null; if ($errors.Count) { $errors; exit 1 }'
```

Expected: subprocess tests and both parser checks pass.

- [ ] **Step 6: Commit Task 2**

```bash
git add dev.sh dev.ps1 tests/scripts/test_dev_launchers.py
git commit -m "fix(dev): make launchers fail fast with local fallback" -- dev.sh dev.ps1 tests/scripts/test_dev_launchers.py
```

---

### Task 3: Atomic graph snapshot refresh

**Files:**
- Modify: `scripts/ensure_seed.py`
- Create: `tests/scripts/test_ensure_seed.py`

**Interfaces:**
- Produces: `seed_transaction_body(sql_content: str) -> str`
- Produces: `apply_seed_snapshot(conn, sql_content: str, seed_hash: str) -> None`
- Preserves: `get_seed_hash` and `is_seeded_and_current`

- [ ] **Step 1: Write failing transaction-body and refresh-order tests**

Use a recording connection/cursor at the external PostgreSQL boundary. The expected cleanup SQL is independently specified in the test and must delete only graph tables in this order:

```python
EXPECTED_GRAPH_REFRESH = """
DELETE FROM public.node_source_references;
DELETE FROM public.decision_edges;
DELETE FROM public.tree_layouts;
DELETE FROM public.decision_nodes;
DELETE FROM public.decision_trees;
""".strip()


def test_seed_transaction_body_removes_only_outer_transaction() -> None:
    sql = "SET client_encoding = 'UTF8';\nBEGIN;\nINSERT INTO x VALUES (1);\nCOMMIT;\n"
    assert seed_transaction_body(sql) == (
        "SET client_encoding = 'UTF8';\nINSERT INTO x VALUES (1);\n"
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
```

- [ ] **Step 2: Run refresh tests and verify RED**

Run: `uv run pytest tests/scripts/test_ensure_seed.py -q`

Expected: import fails because the transaction functions do not exist.

- [ ] **Step 3: Implement minimal graph refresh transaction**

Add a constant containing the five ordered deletes. Implement `seed_transaction_body` to require exactly one standalone `BEGIN;` and final standalone `COMMIT;`, removing only those markers. Implement `apply_seed_snapshot` with one cursor and this order: graph cleanup, stripped seed body, checksum table/upsert, `conn.commit()`. On any exception, call `conn.rollback()` and re-raise; always close the cursor.

- [ ] **Step 4: Add failing rollback and preservation tests**

Configure the recording cursor to raise during the seed statement and assert:

```python
def test_apply_seed_snapshot_rolls_back_when_seed_fails() -> None:
    connection = RecordingConnection(fail_on_statement=2)

    with pytest.raises(psycopg2.DatabaseError):
        apply_seed_snapshot(connection, "BEGIN;\nSELECT 'seed';\nCOMMIT;\n", "abc123")

    assert connection.commits == 0
    assert connection.rollbacks == 1
```

Also assert the cleanup boundary never names `patients`, `visits`, `visit_medications`, `fhir_import_batches`, `development_runtime_logs`, `git_contributions`, `medicines`, `symptoms`, or `contraindication_drugs`.

- [ ] **Step 5: Run rollback tests and verify RED if behavior is incomplete**

Run: `uv run pytest tests/scripts/test_ensure_seed.py -q`

Expected before completing exception handling: rollback assertion fails.

- [ ] **Step 6: Connect snapshot refresh to `main`**

End the read-only checksum transaction before invoking Alembic. Preserve the existing Alembic recovery behavior. After a successful migration, read the seed SQL and call `apply_seed_snapshot`; remove the old direct `cur.execute(sql_content)` and separate metadata commit.

- [ ] **Step 7: Verify Task 3 GREEN**

Run:

```bash
uv run pytest tests/scripts/test_ensure_seed.py tests/scripts/test_dev_database.py tests/scripts/test_dev_launchers.py -q
uv run ruff format scripts/ensure_seed.py tests/scripts/test_ensure_seed.py
uv run ruff check scripts/ensure_seed.py tests/scripts/test_ensure_seed.py
```

Expected: all targeted tests pass and Ruff makes no further changes.

- [ ] **Step 8: Commit Task 3**

```bash
git add scripts/ensure_seed.py tests/scripts/test_ensure_seed.py
git commit -m "fix(dev): refresh stale graph seed atomically" -- scripts/ensure_seed.py tests/scripts/test_ensure_seed.py
```

---

### Task 4: Documentation and full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/getting-started.md`
- Modify: `backups/README.md`

**Interfaces:**
- Documents: zero-config local Compose fallback for the launchers
- Documents: targeted graph refresh and preservation boundary

- [ ] **Step 1: Update onboarding documentation**

Change the quick start to require dependency installation followed by the appropriate launcher. Explain that `.env` is optional for the local Compose workflow and required only to override it. Remove instructions that manually duplicate migrations and seeding before invoking the launcher.

- [ ] **Step 2: Correct seed documentation**

Describe `seed.sql` as data-only SQL containing inserts, updates, and targeted deletes rather than “INSERT statements only.” Document that `ensure_seed.py` refreshes graph tables on checksum change while preserving clinical/dashboard data.

- [ ] **Step 3: Run Python quality checks**

```bash
uv run ruff format --check
uv run ruff check
uv run pyright
uv run pytest -m "not database"
```

Expected: all commands exit 0.

- [ ] **Step 4: Run live disposable-database regression**

With Docker available, create a disposable database, migrate and seed it, replace one seeded node UUID with an older UUID while retaining its `(tree_id, node_key)`, make the checksum stale, and run `ensure_seed.py` again. Verify that the current node UUID is present, representative patient/visit rows remain, and the checksum matches. Drop only the disposable database afterward.

- [ ] **Step 5: Run both live launchers and reload probes**

Run `dev.sh` against the local fallback with no `.env`, verify `/health` and the Vite HTML, edit and restore one Python file and one TypeScript file, and confirm Uvicorn and Vite reload logs. Repeat under `dev.ps1` with native Windows when available; otherwise use PowerShell 7 with the documented macOS `cmd.exe` shim and report the native-cleanup limitation.

- [ ] **Step 6: Run final repository checks**

```bash
git diff --check
git diff --stat
git diff
deploy/run_quality_gates.sh
```

Run the Docker quality gate when Docker is available. Inspect the complete diff and confirm no generated artifacts or unrelated formatter changes were introduced.

- [ ] **Step 7: Commit documentation**

```bash
git add README.md docs/getting-started.md backups/README.md
git commit -m "docs: simplify local development startup" -- README.md docs/getting-started.md backups/README.md
```
