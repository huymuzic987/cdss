from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = (REPO_ROOT / "deploy" / "build_images.sh").read_text(encoding="utf-8")


def test_image_build_fails_fast_when_host_capacity_is_too_low() -> None:
    assert "docker info --format '{{.DockerRootDir}}'" in BUILD_SCRIPT
    assert "MIN_DOCKER_FREE_GB" in BUILD_SCRIPT
    assert "MIN_BUILD_MEMORY_MB" in BUILD_SCRIPT
    assert "docker system df" in BUILD_SCRIPT


def test_low_storage_reclaims_only_unused_buildkit_cache_before_failing() -> None:
    assert "docker builder prune --all --force" in BUILD_SCRIPT
    assert "recheck_available_kb" in BUILD_SCRIPT


def test_build_parallelism_is_bounded_by_current_host_capacity() -> None:
    assert "BUILD_PARALLEL_LIMIT=1" in BUILD_SCRIPT
    assert "BUILD_PARALLEL_LIMIT=2" in BUILD_SCRIPT
    assert 'COMPOSE_PARALLEL_LIMIT="$BUILD_PARALLEL_LIMIT"' in BUILD_SCRIPT
    assert "BUILDKIT_PROGRESS=plain" in BUILD_SCRIPT
    assert "find sort df nproc" in (REPO_ROOT / "Jenkinsfile").read_text(encoding="utf-8")


def test_unchanged_images_are_retagged_without_a_rebuild() -> None:
    assert BUILD_SCRIPT.count("docker image tag") == 2
    assert "backend_hash" in BUILD_SCRIPT
    assert "frontend_hash" in BUILD_SCRIPT
