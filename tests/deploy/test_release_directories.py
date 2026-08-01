from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRUNE_SCRIPT = (REPO_ROOT / "deploy" / "prune_release_dirs.sh").read_text(encoding="utf-8")


def test_release_pruning_requires_a_narrow_absolute_target() -> None:
    assert "CDSS_RELEASES_DIR is required" in PRUNE_SCRIPT
    assert "/*/releases)" in PRUNE_SCRIPT
    assert 'rm -rf -- "$release_dir"' in PRUNE_SCRIPT


def test_release_pruning_preserves_live_and_container_backed_versions() -> None:
    assert 'retained["$CURRENT_VERSION"]=1' in PRUNE_SCRIPT
    assert "docker ps -a --format '{{.Names}}'" in PRUNE_SCRIPT
    assert 'retained["$version"]=1' in PRUNE_SCRIPT
