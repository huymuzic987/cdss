from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WRITE_LOCK_SCRIPT = (REPO_ROOT / "deploy" / "set_write_lock.sh").read_text(
    encoding="utf-8"
)


def test_write_lock_probe_bypasses_http_proxies() -> None:
    assert "curl --noproxy '*'" in WRITE_LOCK_SCRIPT


def test_write_lock_transition_retries_and_reports_http_status() -> None:
    assert 'PROBE_ATTEMPTS="${WRITE_LOCK_PROBE_ATTEMPTS:-10}"' in WRITE_LOCK_SCRIPT
    assert 'for attempt in $(seq 1 "$PROBE_ATTEMPTS")' in WRITE_LOCK_SCRIPT
    assert "Write-lock probe attempt" in WRITE_LOCK_SCRIPT
    assert "! wait_for_probe_status 503" in WRITE_LOCK_SCRIPT
    assert "! wait_for_probe_status 503 not-equal" in WRITE_LOCK_SCRIPT
