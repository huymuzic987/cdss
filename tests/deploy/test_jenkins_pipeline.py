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
    ]

    positions = [stage_position(name) for name in ordered_stages]
    assert positions == sorted(positions)


def test_write_lock_state_is_not_deleted_by_rsync() -> None:
    assert "--exclude 'deploy/.write_lock'" in JENKINSFILE


def test_failure_and_abort_paths_attempt_safe_unlock() -> None:
    assert "failure {" in JENKINSFILE
    assert "aborted {" in JENKINSFILE
    assert JENKINSFILE.count("./deploy/set_write_lock.sh disable") == 3
