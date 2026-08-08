"""Shared Git contribution history parsing for the API and maintenance scripts."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ALIAS_MAP: dict[str, tuple[str, str, str]] = {
    "huymusic987@gmail.com": ("huy", "Huy", "huymuzic987"),
    "huymuzic987": ("huy", "Huy", "huymuzic987"),
    "phamlequangminh2411@gmail.com": (
        "quang_minh",
        "Quang Minh",
        "Quangminh_24112005",
    ),
    "quangminh_24112005": ("quang_minh", "Quang Minh", "Quangminh_24112005"),
    "s4030327@rmit.edu.vn": ("khoa_dang", "Khoa Dang", "Kh04d4n9"),
    "153248299+kh04d4n9@users.noreply.github.com": (
        "khoa_dang",
        "Khoa Dang",
        "Kh04d4n9",
    ),
    "kh04d4n9": ("khoa_dang", "Khoa Dang", "Kh04d4n9"),
    "khoadang": ("khoa_dang", "Khoa Dang", "Kh04d4n9"),
    "s3929597@rmit.edu.vn": ("john_tran", "John Tran", "John Tran"),
    "john tran": ("john_tran", "John Tran", "John Tran"),
    "s4037158@rmit.edu.vn": ("uyen", "NgPhUyen", "NgPhUyen"),
    "ngphuyen": ("uyen", "NgPhUyen", "NgPhUyen"),
}


@dataclass(frozen=True)
class CommitRecord:
    hash: str
    author: str
    message: str
    timestamp: int
    member_keys: tuple[str, ...]


@dataclass(frozen=True)
class GitHistorySnapshot:
    contributors: dict[str, dict[str, Any]]
    commits: tuple[CommitRecord, ...]


def resolve_canonical(name: str, email: str) -> tuple[str, str, str]:
    """Resolve a Git author name/email pair to a canonical team identity."""
    clean_email = email.strip().lower()
    clean_name = name.strip().lower()
    if clean_email in ALIAS_MAP:
        return ALIAS_MAP[clean_email]
    if clean_name in ALIAS_MAP:
        return ALIAS_MAP[clean_name]
    for key, value in ALIAS_MAP.items():
        if key in clean_email or key in clean_name:
            return value
    key = re.sub(r"\W+", "_", clean_name)
    return key, name, email


def _git_ref(scope: str) -> str:
    if scope == "main":
        check_main = subprocess.call(
            ["git", "rev-parse", "--verify", "main"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=PROJECT_ROOT,
        )
        return "main" if check_main == 0 else "HEAD"
    return "--all"


def _commit_authors(name: str, email: str, body: str) -> list[tuple[str, str, str]]:
    primary = resolve_canonical(name, email)
    authors = [primary]
    seen_keys = {primary[0]}
    for line in body.splitlines():
        if not line.strip().lower().startswith("co-authored-by:"):
            continue
        match = re.search(r"co-authored-by:\s*(.*?)\s*<(.*?)>", line, re.IGNORECASE)
        if not match:
            continue
        co_author = resolve_canonical(match.group(1), match.group(2))
        if co_author[0] not in seen_keys:
            authors.append(co_author)
            seen_keys.add(co_author[0])
    return authors


def _parse_git_log(raw_output: str) -> GitHistorySnapshot:
    contributors: dict[str, dict[str, Any]] = {}
    commits: list[CommitRecord] = []

    def get_author(key: str, name: str, email: str) -> dict[str, Any]:
        if key not in contributors:
            contributors[key] = {
                "member_key": key,
                "display_name": name,
                "canonical_email": email,
                "commit_count": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "last_hash": None,
            }
        return contributors[key]

    for block in raw_output.split("\x1e"):
        if not block.strip():
            continue
        fields = block.split("\x1f", 5)
        if len(fields) < 6:
            continue
        hash_str, name, email, timestamp_text, body, numstat_text = fields
        try:
            timestamp = int(timestamp_text)
        except ValueError:
            continue

        commit_authors = _commit_authors(name, email, body)
        for author_key, author_name, author_email in commit_authors:
            author = get_author(author_key, author_name, author_email)
            author["commit_count"] += 1
            if not author["last_hash"]:
                author["last_hash"] = hash_str

        primary_display_name = commit_authors[0][1]
        message = next((line.strip() for line in body.splitlines() if line.strip()), "")
        commits.append(
            CommitRecord(
                hash=hash_str,
                author=primary_display_name,
                message=message,
                timestamp=timestamp,
                member_keys=tuple(author[0] for author in commit_authors),
            )
        )

        weight = 1.0 / len(commit_authors)
        for line in numstat_text.splitlines():
            parts = line.strip().split("\t", 2)
            if len(parts) < 2 or parts[0] == "-" or parts[1] == "-":
                continue
            try:
                added, deleted = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            for author_key, author_name, author_email in commit_authors:
                author = get_author(author_key, author_name, author_email)
                author["lines_added"] += int(added * weight)
                author["lines_deleted"] += int(deleted * weight)

    return GitHistorySnapshot(contributors=contributors, commits=tuple(commits))


def parse_git_history_snapshot(scope: str = "main") -> GitHistorySnapshot:
    """Parse contributor aggregates and canonical commits from local Git history."""
    ref = _git_ref(scope)
    cmd = [
        "git",
        "log",
        ref,
        "--numstat",
        "--no-merges",
        "--pretty=format:%x1e%h%x1f%an%x1f%ae%x1f%at%x1f%B%x1f",
    ]

    try:
        raw_output = subprocess.check_output(
            cmd, cwd=PROJECT_ROOT, encoding="utf-8", errors="ignore"
        )
    except Exception as err:
        print(f"Error executing git log: {err}")
        return GitHistorySnapshot(contributors={}, commits=())

    return _parse_git_log(raw_output)


def parse_git_history(scope: str = "main") -> dict[str, dict[str, Any]]:
    """Preserve the aggregate-only interface used by maintenance scripts."""
    return parse_git_history_snapshot(scope).contributors
