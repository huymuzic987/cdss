from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMOTE_SCRIPT = (REPO_ROOT / "deploy" / "promote_stack.sh").read_text(encoding="utf-8")
CLEANUP_SCRIPT = (REPO_ROOT / "deploy" / "cleanup_failed_stack.sh").read_text(encoding="utf-8")
WRITE_LOCK_SCRIPT = (REPO_ROOT / "deploy" / "set_write_lock.sh").read_text(encoding="utf-8")


def test_promotion_migrates_legacy_frontend_port_owner_to_stable_router() -> None:
    assert 'docker rename "$ROUTER_ID" "$ROUTER_NAME"' in PROMOTE_SCRIPT
    assert 'ROUTER_MODE="legacy"' in PROMOTE_SCRIPT
    assert 'ROUTER_HEALTH_URL="http://127.0.0.1/"' in PROMOTE_SCRIPT
    assert "Refusing to adopt a release container as the stable router." not in PROMOTE_SCRIPT


def test_promotion_writes_state_before_atomic_version_commit() -> None:
    state_move = PROMOTE_SCRIPT.find('mv "$STATE_TMP" "$STATE_FILE"')
    version_move = PROMOTE_SCRIPT.find('mv "$VERSION_TMP" "$VERSION_FILE"')

    assert state_move >= 0
    assert version_move > state_move
    assert "previous_version=%s" in PROMOTE_SCRIPT
    assert "previous_git_commit=%s" in PROMOTE_SCRIPT


def test_automatic_rollback_requires_active_write_lock() -> None:
    rollback_condition = CLEANUP_SCRIPT.find('if [ -f "$WRITE_LOCK_FILE" ]')
    rollback_command = CLEANUP_SCRIPT.find(
        'bash deploy/promote_stack.sh "$PREVIOUS_VERSION" rollback'
    )

    assert rollback_condition >= 0
    assert rollback_command > rollback_condition


def test_write_lock_probe_allows_router_reload_to_settle() -> None:
    assert "wait_for_probe_status()" in WRITE_LOCK_SCRIPT
    assert "for attempt in $(seq 1 10); do" in WRITE_LOCK_SCRIPT
    assert 'wait_for_probe_status "503"' in WRITE_LOCK_SCRIPT
