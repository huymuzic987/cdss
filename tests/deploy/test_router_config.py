import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERER = "deploy/render_router_config.sh"


def render(write_lock_enabled: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(RENDERER), "142", "cdss-frontend-142", write_lock_enabled],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_locked_router_blocks_only_known_mutating_routes() -> None:
    result = render("true")

    assert result.returncode == 0, result.stderr
    assert "~^(PUT|PATCH|DELETE):/trees/[^/]+/layout$ 1;" in result.stdout
    assert "~^POST:/fhir/import$ 1;" in result.stdout
    assert "~^POST:/dashboard/seed$ 1;" in result.stdout
    assert "~^POST:/__deployment/write-lock-probe$ 1;" in result.stdout
    assert "POST:/evaluate" not in result.stdout
    assert "Retry-After" in result.stdout
    assert 'add_header X-CDSS-Release "142" always;' in result.stdout
    assert "set $release_upstream http://cdss-frontend-142;" in result.stdout


def test_unlocked_router_has_no_blocked_route_entries() -> None:
    result = render("false")

    assert result.returncode == 0, result.stderr
    assert "default 0;" in result.stdout
    assert "/trees/[^/]+/layout" not in result.stdout
    assert "POST:/fhir/import" not in result.stdout
    assert "POST:/dashboard/seed" not in result.stdout
    assert "POST:/__deployment/write-lock-probe" not in result.stdout


def test_renderer_rejects_invalid_lock_state() -> None:
    result = render("unexpected")

    assert result.returncode == 2
    assert "must be true or false" in result.stderr
