"""Guard the production-module size boundary established by the refactor."""

from pathlib import Path

MAX_CODE_LINES = 200
SOURCE_ROOT = Path("src/cdss")


def _is_excluded(path: Path) -> bool:
    relative = path.relative_to(SOURCE_ROOT)
    return (
        relative.parts[:2] == ("api", "schemas")
        or relative.parts[0] == "testing"
        or relative.as_posix() == "infrastructure/db/models.py"
    )


def _code_line_count(path: Path) -> int:
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_behavior_modules_do_not_exceed_200_code_lines() -> None:
    oversized = {
        path.relative_to(SOURCE_ROOT).as_posix(): _code_line_count(path)
        for path in SOURCE_ROOT.rglob("*.py")
        if not _is_excluded(path) and _code_line_count(path) > MAX_CODE_LINES
    }

    assert oversized == {}, f"Behavior modules exceed {MAX_CODE_LINES} code lines: {oversized}"
