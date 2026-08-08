"""Tests for canonical Git contribution history parsing."""

from __future__ import annotations

from cdss.infrastructure.git_contributions import parse_git_history_snapshot

RAW_LOG = (
    "\x1eabc1234\x1fHuy\x1fhuymusic987@gmail.com\x1f1782691200\x1f"
    "feat: add chart history\n\n"
    "Co-authored-by: Quang Minh <phamlequangminh2411@gmail.com>\n"
    "\x1f\n10\t2\tfrontend/chart.tsx\n"
    "\x1edef5678\x1fHuy\x1fhuymusic987@gmail.com\x1f1782777600\x1f"
    "fix: correct velocity\n"
    "\x1f\n4\t1\tfrontend/velocity.tsx\n"
)


def test_parse_git_history_snapshot_keeps_real_commits_and_canonical_authors(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "cdss.infrastructure.git_contributions.subprocess.check_output",
        lambda *args, **kwargs: RAW_LOG,
    )
    monkeypatch.setattr(
        "cdss.infrastructure.git_contributions.subprocess.call",
        lambda *args, **kwargs: 0,
    )

    snapshot = parse_git_history_snapshot("main")

    assert [commit.hash for commit in snapshot.commits] == ["abc1234", "def5678"]
    assert snapshot.commits[0].message == "feat: add chart history"
    assert snapshot.commits[0].member_keys == ("huy", "quang_minh")
    assert snapshot.contributors["huy"]["commit_count"] == 2
    assert snapshot.contributors["quang_minh"]["commit_count"] == 1
    assert snapshot.contributors["huy"]["lines_added"] == 9
    assert snapshot.contributors["quang_minh"]["lines_added"] == 5
