from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QUALITY_SCRIPT = (REPO_ROOT / "deploy" / "run_quality_gates.sh").read_text(encoding="utf-8")
FRONTEND_SCRIPT = (REPO_ROOT / "deploy" / "run_frontend_quality_gates.sh").read_text(
    encoding="utf-8"
)


def test_ci_resources_are_namespaced_per_build() -> None:
    assert 'RAW_CI_RUN_ID="${BUILD_TAG:-local-$$}"' in QUALITY_SCRIPT
    assert 'NETWORK="cdss-ci-${CI_RUN_ID}-net"' in QUALITY_SCRIPT
    assert 'POSTGRES_CONTAINER="cdss-ci-${CI_RUN_ID}-postgres"' in QUALITY_SCRIPT
    assert 'docker rm -f "$POSTGRES_CONTAINER"' in QUALITY_SCRIPT
    assert 'docker network rm "$NETWORK"' in QUALITY_SCRIPT


def test_dependency_caches_persist_in_named_volumes() -> None:
    assert 'UV_CACHE_VOLUME="cdss-ci-uv-cache-py312"' in QUALITY_SCRIPT
    assert 'UV_ENV_VOLUME="cdss-ci-uv-env-py312"' in QUALITY_SCRIPT
    assert 'PNPM_STORE_VOLUME="cdss-ci-pnpm-store-v9"' in QUALITY_SCRIPT
    assert '-v "$UV_CACHE_VOLUME":/uv-cache' in QUALITY_SCRIPT
    assert '-v "$UV_ENV_VOLUME":/venv' in QUALITY_SCRIPT
    assert '-v "$PNPM_STORE_VOLUME":/pnpm/store' in QUALITY_SCRIPT
    assert 'PNPM_STORE_DIR="${PNPM_STORE_DIR:-/tmp/pnpm-store}"' in FRONTEND_SCRIPT


def test_backend_and_frontend_branches_run_before_either_wait() -> None:
    backend_start = QUALITY_SCRIPT.find("run_backend_quality_gates &")
    frontend_start = QUALITY_SCRIPT.find("run_frontend_quality_gates &")
    first_wait = QUALITY_SCRIPT.find('wait "$backend_gate_pid"')

    assert backend_start >= 0
    assert frontend_start > backend_start
    assert first_wait > frontend_start
    assert 'wait "$frontend_gate_pid"' in QUALITY_SCRIPT
