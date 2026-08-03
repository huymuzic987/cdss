"""Shared Git contribution history parsing for the API and maintenance scripts."""

from __future__ import annotations

import re
import subprocess
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


def parse_git_history(scope: str = "main") -> dict[str, dict[str, Any]]:
    """Parse commit and numstat data from the local Git history."""
    ref = "main" if scope == "main" else "--all"
    cmd = [
        "git",
        "log",
        ref,
        "--numstat",
        "--no-merges",
        "--pretty=format:COMMIT_START|%h|%an|%ae|%at|%B|COMMIT_END",
    ]

    try:
        raw_output = subprocess.check_output(
            cmd, cwd=PROJECT_ROOT, encoding="utf-8", errors="ignore"
        )
    except Exception as err:
        print(f"Error executing git log: {err}")
        return {}

    authors: dict[str, dict[str, Any]] = {}

    def get_author_dict(m_key: str, d_name: str, c_email: str) -> dict[str, Any]:
        if m_key not in authors:
            authors[m_key] = {
                "member_key": m_key,
                "display_name": d_name,
                "canonical_email": c_email,
                "commit_count": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "last_hash": None,
            }
        return authors[m_key]

    blocks = raw_output.split("COMMIT_START|")
    for block in blocks:
        if not block.strip():
            continue

        parts = block.split("|COMMIT_END", 1)
        commit_header = parts[0]
        numstat_lines = parts[1].splitlines() if len(parts) > 1 else []

        header_fields = commit_header.split("|", 4)
        if len(header_fields) < 5:
            continue

        hash_str, name, email, _timestamp, body = header_fields
        member_key, display_name, canonical_email = resolve_canonical(name, email)

        co_author_keys: set[tuple[str, str, str]] = set()
        for line in body.splitlines():
            line_str = line.strip()
            if line_str.lower().startswith("co-authored-by:"):
                co_match = re.search(r"co-authored-by:\s*(.*?)\s*<(.*?)>", line_str, re.IGNORECASE)
                if co_match:
                    co_name, co_email = co_match.group(1), co_match.group(2)
                    co_key, co_display_name, co_canonical_email = resolve_canonical(
                        co_name, co_email
                    )
                    if co_key != member_key:
                        co_author_keys.add((co_key, co_display_name, co_canonical_email))

        all_commit_authors = [
            (member_key, display_name, canonical_email),
            *co_author_keys,
        ]
        weight = 1.0 / len(all_commit_authors)

        for author_key, author_name, author_email in all_commit_authors:
            author = get_author_dict(author_key, author_name, author_email)
            author["commit_count"] += 1
            if not author["last_hash"]:
                author["last_hash"] = hash_str

        for line in numstat_lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            num_parts = line.split()
            if len(num_parts) >= 2 and num_parts[0] != "-" and num_parts[1] != "-":
                added = int(num_parts[0])
                deleted = int(num_parts[1])
                for author_key, author_name, author_email in all_commit_authors:
                    author = get_author_dict(author_key, author_name, author_email)
                    author["lines_added"] += int(added * weight)
                    author["lines_deleted"] += int(deleted * weight)

    return authors
