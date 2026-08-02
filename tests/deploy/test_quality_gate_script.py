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
    assert 'PNPM_MODULES_VOLUME="cdss-ci-pnpm-modules-v9"' in QUALITY_SCRIPT
    assert 'docker volume create "$PNPM_MODULES_VOLUME"' in QUALITY_SCRIPT
    assert '-v "$PNPM_MODULES_VOLUME":/workspace/node_modules' in QUALITY_SCRIPT
    assert 'PNPM_STORE_DIR="${PNPM_STORE_DIR:-/tmp/pnpm-store}"' in FRONTEND_SCRIPT


def test_backend_and_frontend_branches_run_before_either_wait() -> None:
    backend_start = QUALITY_SCRIPT.find("run_backend_quality_gates &")
    frontend_start = QUALITY_SCRIPT.find("run_frontend_quality_gates &")
    first_wait = QUALITY_SCRIPT.find('wait "$backend_gate_pid"')

    assert backend_start >= 0
    assert frontend_start > backend_start
    assert first_wait > frontend_start
    assert 'wait "$frontend_gate_pid"' in QUALITY_SCRIPT


def test_backend_pytest_and_pyright_are_concurrent_and_status_checked() -> None:
    pyright_start = QUALITY_SCRIPT.find(
        'timed backend-pyright uv run pyright &'
    )
    pytest_start = QUALITY_SCRIPT.find(
        'if timed backend-pytest uv run pytest'
    )
    pyright_wait = QUALITY_SCRIPT.find(r'wait "\$pyright_pid"')
    status_guard = QUALITY_SCRIPT.find(
        r'if [ "\$pytest_status" -ne 0 ] || [ "\$pyright_status" -ne 0 ]; then'
    )

    assert pyright_start >= 0
    assert r'pyright_pid=\$!' in QUALITY_SCRIPT
    assert pytest_start > pyright_start
    assert pyright_wait > pytest_start
    assert r'pytest_status=\$?' in QUALITY_SCRIPT
    assert r'pyright_status=\$?' in QUALITY_SCRIPT
    assert status_guard > pyright_wait


def test_quality_gates_generate_junit_and_coverage_reports() -> None:
    assert "--junitxml=.ci-reports/backend/junit.xml" in QUALITY_SCRIPT
    assert "--cov-report=xml:.ci-reports/backend/coverage.xml" in QUALITY_SCRIPT
    assert "--reporter=junit" in FRONTEND_SCRIPT
    assert "--outputFile.junit=./.ci-reports/junit.xml" in FRONTEND_SCRIPT
    assert ".ci-reports/timings.tsv" in QUALITY_SCRIPT
    assert ".ci-reports/timings.tsv" in FRONTEND_SCRIPT
