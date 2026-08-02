# CI/CD Performance Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce warm-cache Jenkins execution time toward a consistent sub-two-minute result while retaining every existing quality gate and deployment validation.

**Architecture:** Keep the current backend/frontend quality-gate branches running concurrently. Add a persistent frontend node_modules volume, overlap only backend Pytest and Pyright after dependency setup, and reduce candidate PostgreSQL polling granularity while preserving a finite readiness budget. Production image-build parallelism and deployment promotion/recovery behavior remain unchanged.

**Tech Stack:** Bash 5 on Jenkins/Linux, Docker, uv, Python 3.12, pytest, Ruff, Pyright, Node 24, pnpm 9.15.9, Vitest, Oxlint, TypeScript, Vite, PostgreSQL 16, pytest static deployment tests.

## Global Constraints

- Retain all backend and frontend quality gates on every normal build.
- The frontend quality-gate script continues to run `pnpm install --frozen-lockfile` on every build.
- Any failed quality gate continues to fail the pipeline.
- Keep a finite retry limit for candidate PostgreSQL readiness.
- Do not increase Docker build concurrency on the current approximately 3.5 GiB deployment host.
- Do not introduce a registry, artifact promotion, selective tests, or a new deployment architecture.
- Preserve machine-readable timing, JUnit, and coverage evidence.
- The two-minute objective is an operational acceptance target, not a new hard quality gate.

---

## File Map

- Modify: `tests/deploy/test_quality_gate_script.py` to cover the persistent frontend dependency volume and backend status aggregation.
- Modify: `tests/deploy/test_database_deploy_validation.py` to cover frequent but bounded candidate database readiness polling.
- Modify: `deploy/run_quality_gates.sh` to create/mount the frontend dependency volume and overlap Pytest with Pyright.
- Modify: `deploy/provision_stack.sh` to poll candidate PostgreSQL readiness once per second with the same approximately two-minute maximum budget.
- Use: `docs/ci-cd-baseline.md` as the measurement format for post-change Jenkins evidence; only append measured values after the required successful builds exist.

## Interfaces Between Tasks

- The regression tests define these source-level invariants:
  - `PNPM_MODULES_VOLUME="cdss-ci-pnpm-modules-v9"` is created and mounted at `/workspace/node_modules`.
  - `backend-pyright` runs in the background, its PID is waited on, and both Pytest and Pyright statuses are checked.
  - Candidate database readiness uses `seq 1 120` with `sleep 1`, preserving the old approximately 120-second maximum wait.
- `deploy/run_frontend_quality_gates.sh` remains the owner of dependency installation and all four frontend gates; no caller bypasses it.
- `deploy/provision_stack.sh` continues to emit `candidate-database-ready` timing records and exits nonzero when readiness is not achieved.

### Task 1: Add failing regression tests for the performance invariants

**Files:**
- Modify: `tests/deploy/test_quality_gate_script.py:18-45`
- Modify: `tests/deploy/test_database_deploy_validation.py:103-111`

**Interfaces:**
- Consumes: the current shell-script source strings loaded into `QUALITY_SCRIPT`, `FRONTEND_SCRIPT`, and `provision`.
- Produces: failing tests that specify the exact cache mount, backend process-status, and readiness-loop contracts required by Tasks 2 and 3.

- [ ] **Step 1: Extend the dependency-cache test with the persistent frontend modules volume.**

Add these assertions to `test_dependency_caches_persist_in_named_volumes` after the existing pnpm-store assertions:

~~~
    assert 'PNPM_MODULES_VOLUME="cdss-ci-pnpm-modules-v9"' in QUALITY_SCRIPT
    assert 'docker volume create "$PNPM_MODULES_VOLUME"' in QUALITY_SCRIPT
    assert '-v "$PNPM_MODULES_VOLUME":/workspace/node_modules' in QUALITY_SCRIPT
~~~

- [ ] **Step 2: Add a failing backend-concurrency/status test.**

Add this test after `test_backend_and_frontend_branches_run_before_either_wait`:

~~~
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
~~~

- [ ] **Step 3: Add a failing readiness-polling test.**

Add this test after `test_database_validation_precedes_candidate_service_start`:

~~~
def test_candidate_database_readiness_is_frequent_but_bounded() -> None:
    provision = (REPO_ROOT / "deploy" / "provision_stack.sh").read_text(
        encoding="utf-8"
    )
    readiness_start = provision.index(
        'echo "Waiting for database to be ready..."'
    )
    readiness_end = provision.index(
        'if [ "$db_ready" != "true" ]', readiness_start
    )
    readiness_block = provision[readiness_start:readiness_end]

    assert "for i in $(seq 1 120); do" in readiness_block
    assert "sleep 1" in readiness_block
    assert "sleep 5" not in readiness_block
~~~

- [ ] **Step 4: Run the new targeted tests and verify they fail for the intended missing source changes.**

Run:

~~~
pytest -q tests/deploy/test_quality_gate_script.py tests/deploy/test_database_deploy_validation.py
~~~

Expected: the new assertions fail because the current quality-gate script has no PNPM_MODULES_VOLUME, the backend checks are sequential, and candidate provisioning still uses seq 1 24 with sleep 5. Existing unrelated tests must remain passing.

- [ ] **Step 5: Commit the regression tests.**

~~~
git add tests/deploy/test_quality_gate_script.py tests/deploy/test_database_deploy_validation.py
git commit -m "test: cover CI/CD performance invariants"
~~~

### Task 2: Reuse frontend dependencies and overlap backend Pytest/Pyright

**Files:**
- Modify: `deploy/run_quality_gates.sh:29-31,117-133,223-273`
- Test: `tests/deploy/test_quality_gate_script.py`

**Interfaces:**
- Consumes: the failing source-level invariants from Task 1 and the existing run_frontend_quality_gates contract.
- Produces: a named cdss-ci-pnpm-modules-v9 volume mounted only for the frontend quality-gate container, plus explicit pytest_status and pyright_status aggregation inside the backend container.

- [ ] **Step 1: Add and create the frontend modules volume.**

Add the constant beside PNPM_STORE_VOLUME:

~~~
PNPM_MODULES_VOLUME="cdss-ci-pnpm-modules-v9"
~~~

Create it beside the existing persistent volumes:

~~~
docker volume create "$PNPM_MODULES_VOLUME" > /dev/null
~~~

Do not remove this volume in cleanup(). It is intentionally persistent, and it is not part of the bind-mounted workspace that Jenkins must delete.

- [ ] **Step 2: Mount the modules volume in the frontend quality-gate container.**

Add the mount immediately after the pnpm-store mount in run_frontend_quality_gates:

~~~
    -v "$PNPM_MODULES_VOLUME":/workspace/node_modules \
~~~

Leave deploy/run_frontend_quality_gates.sh unchanged for this task: it must still configure PNPM_STORE_DIR and run pnpm install --frozen-lockfile before Vitest, Oxlint, TypeScript, and Vite.

- [ ] **Step 3: Replace the sequential backend Pytest/Pyright block with bounded status aggregation.**

Inside the quoted backend container script, keep dependency synchronization and the runtime check first, then use this exact control flow around the existing full Pytest command:

~~~
        timed backend-dependency-sync uv sync --frozen
        timed pyright-runtime-check uv run pyright --version
        pyright_status=0
        timed backend-pyright uv run pyright &
        pyright_pid=\$!
        if timed backend-pytest uv run pytest \
            --junitxml=.ci-reports/backend/junit.xml \
            --cov=cdss \
            --cov-report=term-missing \
            --cov-report=xml:.ci-reports/backend/coverage.xml; then
            pytest_status=0
        else
            pytest_status=\$?
        fi
        if wait "\$pyright_pid"; then
            pyright_status=0
        else
            pyright_status=\$?
        fi
        timed backend-ruff-check uv run ruff check
        timed backend-ruff-format uv run ruff format --check
        if [ "\$pytest_status" -ne 0 ] || [ "\$pyright_status" -ne 0 ]; then
            exit 1
        fi
~~~

The if wrappers are required because the container shell uses set -e; they allow both concurrent statuses to be observed instead of letting one process hide the other. Keep the existing timed function and all report paths unchanged.

- [ ] **Step 4: Run the targeted quality-gate tests and shell syntax checks.**

Run:

~~~
pytest -q tests/deploy/test_quality_gate_script.py
bash -n deploy/run_quality_gates.sh
bash -n deploy/run_frontend_quality_gates.sh
~~~

Expected: all quality-gate static tests pass, including the named-volume, branch-overlap, JUnit, coverage, and timing assertions; both scripts pass Bash syntax validation.

- [ ] **Step 5: Commit the quality-gate optimization.**

~~~
git add deploy/run_quality_gates.sh tests/deploy/test_quality_gate_script.py
git commit -m "perf: cache frontend dependencies and overlap backend checks"
~~~

### Task 3: Reduce candidate database readiness polling delay

**Files:**
- Modify: `deploy/provision_stack.sh:31-49`
- Test: `tests/deploy/test_database_deploy_validation.py`

**Interfaces:**
- Consumes: the readiness-loop invariant from Task 1.
- Produces: the same db_ready success/failure behavior and timing record with one-second polling and an approximately 120-second maximum wait.

- [ ] **Step 1: Replace only the candidate database polling interval and retry count.**

Change the existing loop from 24 five-second attempts to 120 one-second attempts, preserving the command, db_ready flag, failure logging, and CDSS_TIMING output:

~~~
for i in $(seq 1 120); do
    if $COMPOSE exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        db_ready=true
        break
    fi
    sleep 1
done
~~~

Do not alter the migration, seed, candidate validation, service-health, promotion, router, or write-lock stages.

- [ ] **Step 2: Run the deployment validation tests and syntax check.**

Run:

~~~
pytest -q tests/deploy/test_database_deploy_validation.py
bash -n deploy/provision_stack.sh
~~~

Expected: all database deployment validation tests pass, including the ordering assertion that candidate validation precedes service start; the provisioning script passes syntax validation.

- [ ] **Step 3: Commit the readiness optimization.**

~~~
git add deploy/provision_stack.sh tests/deploy/test_database_deploy_validation.py
git commit -m "perf: poll candidate database readiness more frequently"
~~~

### Task 4: Run full validation and collect performance evidence

**Files:**
- Inspect: `docs/ci-cd-baseline.md`
- Update only after measurements: `docs/ci-cd-baseline.md`

**Interfaces:**
- Consumes: the committed changes from Tasks 1–3 and the existing Jenkins CDSS_TIMING records.
- Produces: verified quality-gate evidence and a post-change comparison of total duration, critical-path gates, resource pressure, and deployment success.

- [ ] **Step 1: Run the full deployment-test regression set supported by the local environment.**

Run:

~~~
pytest -q tests/deploy/test_quality_gate_script.py tests/deploy/test_database_deploy_validation.py tests/deploy/test_jenkins_pipeline.py tests/deploy/test_image_build_optimization.py
~~~

Expected: all selected deployment regression tests pass. If the local macOS Bash version cannot execute Linux-only deployment shell tests, record that limitation and use Jenkins/Linux for the authoritative full validation rather than weakening the tests.

- [ ] **Step 2: Run the complete local quality gate when Docker is available.**

Run:

~~~
./deploy/run_quality_gates.sh
~~~

Expected: backend and frontend branches both pass; all existing JUnit, coverage, and CDSS_TIMING artifacts are generated. This command must not be replaced with an abbreviated test selection.

- [ ] **Step 3: Run the authoritative Jenkins validation and deployment.**

Trigger the normal main-branch Jenkins job on the target Linux host. Confirm the log contains, at minimum:

~~~
Backend quality-gate branch passed.
Frontend quality-gate branch passed.
All quality gates passed.
Production environment file validated.
Candidate database validation
Verify Public Endpoint
Finished: SUCCESS
~~~

Confirm the full validation path remains present: FHIR generation, migrations, seed, backend Pytest/Ruff/Pyright, frontend Vitest/Oxlint/TypeScript/Vite, image build, candidate database validation, service health, promotion, public endpoint verification, and write-lock disablement.

- [ ] **Step 4: Collect at least ten successful post-change builds.**

For every successful sample, record the build number, commit, cache state, image work, database size, total execution, quality-gate duration, image-build duration, candidate provisioning duration, and public verification duration in the format defined by docs/ci-cd-baseline.md. Include at least two cold-cache samples and two samples rebuilding both images.

- [ ] **Step 5: Append measured post-change results without replacing the original baseline.**

After the ten successful samples exist, add a clearly labeled after-change table to docs/ci-cd-baseline.md. Use observed values only. Do not add a hard Jenkins timing failure based on this table; host load, Docker cache state, and Jenkins queue time remain external variables.

- [ ] **Step 6: Review acceptance criteria before declaring completion.**

Confirm:

- all backend and frontend gates pass with evidence artifacts;
- the deployment recovery and public-endpoint behavior is unchanged;
- warm-cache builds consistently meet the sub-two-minute operational target on the target host;
- deployment-host resource pressure and failure rate did not materially increase;
- any remaining critical-path stage is identified if the target is not reached.

## Spec Coverage Self-Review

- Full validation retention is covered by Tasks 2 and 4, including the unchanged frozen install and all named gates.
- Frontend dependency reuse is covered by Task 2 and its mount regression test.
- Bounded backend Pytest/Pyright concurrency and exit-status propagation are covered by Tasks 1 and 2.
- One-second but finite candidate readiness polling is covered by Tasks 1 and 3.
- Low-memory image-build policy and deployment safety behavior are explicitly preserved by the Global Constraints and Task 4 checks.
- Timing, JUnit, coverage, and ten-build measurement requirements are covered by Tasks 2 and 4.
- No selective tests, artifact handoff, registry, or hard performance gate is introduced.

## Execution Order

Execute Tasks 1 through 4 in order. Task 1 must fail before Tasks 2 and 3 change the implementation. Tasks 2 and 3 can be reviewed independently after their targeted tests pass. Task 4 is the final verification and measurement checkpoint.
