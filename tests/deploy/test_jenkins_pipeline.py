from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
JENKINSFILE = (REPO_ROOT / "Jenkinsfile").read_text(encoding="utf-8")


def stage_position(name: str) -> int:
    marker = f"stage('{name}')"
    position = JENKINSFILE.find(marker)
    assert position >= 0, f"missing Jenkins stage: {name}"
    return position


def test_write_lock_spans_database_clone_through_public_verification() -> None:
    ordered_stages = [
        "Backup Current Database",
        "Enable Write Lock",
        "Provision New Stack",
        "Promote New Stack",
        "Verify Public Endpoint",
        "Disable Write Lock",
        "Prune Old Stacks",
        "Record Deployment Evidence",
    ]

    positions = [stage_position(name) for name in ordered_stages]
    assert positions == sorted(positions)


def test_write_lock_state_is_not_deleted_by_rsync() -> None:
    assert "--exclude 'deploy/.write_lock'" in JENKINSFILE
    assert "--exclude 'deploy/.deployment_state'" in JENKINSFILE
    assert "ln -sfn ${DEPLOY_PATH}/shared" in JENKINSFILE


def test_failure_and_abort_paths_attempt_safe_unlock() -> None:
    assert "failure {" in JENKINSFILE
    assert "aborted {" in JENKINSFILE
    assert JENKINSFILE.count("./deploy/set_write_lock.sh disable") == 3


def test_pruning_waits_for_external_verification_and_write_resume() -> None:
    assert stage_position("Verify Public Endpoint") < stage_position("Disable Write Lock")
    assert stage_position("Disable Write Lock") < stage_position("Prune Old Stacks")


def test_git_commit_is_passed_to_promotion() -> None:
    assert "DEPLOY_GIT_COMMIT=${GIT_COMMIT}" in JENKINSFILE


def test_pipeline_has_global_execution_and_retention_guards() -> None:
    assert "timeout(time: 90, unit: 'MINUTES')" in JENKINSFILE
    assert "buildDiscarder(logRotator(" in JENKINSFILE
    assert "disableRestartFromStage()" in JENKINSFILE
    assert "skipStagesAfterUnstable()" in JENKINSFILE


def test_every_stage_has_a_timeout() -> None:
    stage_names = [
        "Checkout",
        "Verify Files",
        "Quality Gates",
        "Deploy Files",
        "Inject Environment",
        "Ensure Live Route",
        "Build Images",
        "Backup Current Database",
        "Enable Write Lock",
        "Provision New Stack",
        "Promote New Stack",
        "Verify Public Endpoint",
        "Disable Write Lock",
        "Prune Old Stacks",
        "Record Deployment Evidence",
    ]

    for name in stage_names:
        stage_start = stage_position(name)
        stage_prefix = JENKINSFILE[stage_start : stage_start + 180]
        assert "options { timeout(" in stage_prefix, f"stage has no timeout: {name}"


def test_agent_capabilities_fail_fast() -> None:
    assert 'if [ "$(uname -s)" != "Linux" ]' in JENKINSFILE
    assert "docker info > /dev/null" in JENKINSFILE
    assert "rsync curl awk sed grep" in JENKINSFILE


def test_reports_are_published_before_workspace_cleanup() -> None:
    assert "junit(" in JENKINSFILE
    assert ".ci-reports/backend/junit.xml" in JENKINSFILE
    assert "frontend/.ci-reports/junit.xml" in JENKINSFILE
    archive_position = JENKINSFILE.find("archiveArtifacts(")
    cleanup_position = JENKINSFILE.find("cleanWs()")
    assert archive_position >= 0
    assert cleanup_position > archive_position


def test_deployment_evidence_contains_no_environment_file() -> None:
    assert "stage('Record Deployment Evidence')" in JENKINSFILE
    assert ".ci-reports/deployment/state.txt" in JENKINSFILE
    assert "artifacts: '.ci-reports/**/*,frontend/.ci-reports/**/*'" in JENKINSFILE


def test_environment_is_private_and_validated_before_replacement() -> None:
    private_create = JENKINSFILE.find("umask 077")
    validate = JENKINSFILE.find("./deploy/validate_env.sh ${DEPLOY_PATH}/shared/.env.new")
    replace = JENKINSFILE.find("mv -f ${DEPLOY_PATH}/shared/.env.new")

    assert private_create >= 0
    assert validate > private_create
    assert replace > validate


def test_deployments_use_isolated_release_directories_and_shared_state() -> None:
    release_path = "${DEPLOY_PATH}/releases/${VERSION}"

    assert f"${{TARGET_SERVER}}:{release_path}/" in JENKINSFILE
    assert JENKINSFILE.count(f"cd {release_path}") >= 9
    assert "ln -sfn ${DEPLOY_PATH}/shared/.env" in JENKINSFILE
    assert r"\$release_path/deploy/state" in JENKINSFILE
    assert "${DEPLOY_PATH}/shared/.deployment_state" in JENKINSFILE
    assert "./deploy/prune_release_dirs.sh" in JENKINSFILE
