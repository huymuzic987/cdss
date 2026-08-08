from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FALLBACK_URL = "postgresql://cdss:cdss@127.0.0.1:54321/cdss"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _fake_external_commands(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "uv",
        f"""#!/usr/bin/env bash
set -eu
if [ "$1" = "run" ] && [ "$2" = "python" ] && [ "$3" = "scripts/dev_database.py" ]; then
    case "${{4:-}}" in
        resolve) exec {shlex.quote(sys.executable)} scripts/dev_database.py resolve ;;
        wait)
            if [ "${{FAKE_UV_WAIT_EXIT:-0}}" -ne 0 ]; then
                echo "Could not connect to PostgreSQL at 127.0.0.1:54321/cdss" \\
                    "after 30 attempts." >&2
                exit "$FAKE_UV_WAIT_EXIT"
            fi
            exit 0
            ;;
    esac
fi
if [ "$1" = "run" ] && [ "$2" = "python" ] && [ "$3" = "scripts/ensure_seed.py" ]; then
    printf '%s\\n' "${{DATABASE_URL:-}}" >> "$RECORDED_DATABASE_URLS"
    exit 0
fi
if [ "$1" = "run" ] && [ "$2" = "uvicorn" ]; then
    printf '%s\\n' "${{DATABASE_URL:-}}" >> "$RECORDED_DATABASE_URLS"
    exit 0
fi
if [ "$1" = "run" ] && [ "$2" = "python" ] && [ "$3" = "-c" ]; then
    exit 0
fi
exit 0
""",
    )
    for command in ("docker", "docker-compose", "docker.exe", "pnpm", "cmd.exe"):
        _write_executable(bin_dir / command, "#!/usr/bin/env bash\nexit 0\n")
    return bin_dir


def _isolated_launcher_root(tmp_path: Path, launcher: str) -> Path:
    launcher_root = tmp_path / "launcher-root"
    scripts_dir = launcher_root / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(SOURCE_ROOT / launcher, launcher_root / launcher)
    shutil.copy2(SOURCE_ROOT / "scripts" / "dev_database.py", scripts_dir / "dev_database.py")
    return launcher_root


def run_launcher(
    launcher: str, tmp_path: Path, *, environ: Mapping[str, str], wait_exit: int = 0
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = _fake_external_commands(tmp_path)
    launcher_root = _isolated_launcher_root(tmp_path, launcher)
    recorded_urls = tmp_path / "database-urls.txt"
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env.update(environ)
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "RECORDED_DATABASE_URLS": str(recorded_urls),
            "FAKE_UV_WAIT_EXIT": str(wait_exit),
        }
    )
    if launcher == "dev.sh":
        command = ["bash", "dev.sh"]
    else:
        command = ["pwsh", "-NoLogo", "-NoProfile", "-File", "dev.ps1"]
    result = subprocess.run(command, cwd=launcher_root, env=env, text=True, capture_output=True)
    return result, recorded_urls.read_text(
        encoding="utf-8"
    ).splitlines() if recorded_urls.exists() else []


def test_bash_launcher_exports_compose_fallback_to_seed_and_backend(tmp_path: Path) -> None:
    result, recorded_urls = run_launcher("dev.sh", tmp_path, environ={})

    assert result.returncode == 0, result.stderr
    assert recorded_urls == [COMPOSE_FALLBACK_URL, COMPOSE_FALLBACK_URL]


def test_bash_launcher_preserves_explicit_database_url(tmp_path: Path) -> None:
    result, recorded_urls = run_launcher(
        "dev.sh", tmp_path, environ={"DATABASE_URL": "postgresql://explicit/db"}
    )

    assert result.returncode == 0, result.stderr
    assert recorded_urls == ["postgresql://explicit/db", "postgresql://explicit/db"]


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell is not installed")
def test_powershell_launcher_reports_database_failure_not_docker_failure(tmp_path: Path) -> None:
    result, _recorded_urls = run_launcher("dev.ps1", tmp_path, environ={}, wait_exit=1)

    assert result.returncode == 1
    assert "Could not connect to PostgreSQL at" in result.stderr
    assert "Make sure Docker Desktop or WSL Docker daemon is running" not in result.stdout


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell is not installed")
def test_powershell_launcher_exports_compose_fallback_to_seed_and_backend(tmp_path: Path) -> None:
    result, recorded_urls = run_launcher("dev.ps1", tmp_path, environ={})

    assert result.returncode == 0, result.stderr
    assert recorded_urls == [COMPOSE_FALLBACK_URL, COMPOSE_FALLBACK_URL]
